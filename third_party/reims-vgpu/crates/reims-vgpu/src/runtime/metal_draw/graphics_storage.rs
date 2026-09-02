//! Graphics texture access is part of the shader contract, not a sampled-only
//! binding convention. This conservative rail writes independent native 2D
//! guest views synchronously; aliasing views and unproven backings decline.

use super::{DrawEncodeRequest, MAX_BIND_SLOTS};
use crate::backend::vulkan::engine::descriptor_contract::DescriptorContractDecline;
use crate::backend::vulkan::engine::{self, DrawError, GraphicsStorageImageResource};
use crate::model::DeviceState;
use crate::runtime::compute_exec::{self, GraphicsStagedTexture};
use crate::runtime::host::{HostMemory, HostOps};
use crate::runtime::spirv_bind::{
    self, ImageAccess, ImageFormat, ReflectedComputeTexture, StorageImageAccess,
    FRAG_SAMPLED_RESOURCE_BINDING_OFFSET, TEXTURE_BINDING_BASE,
};
use metal2vulkan::reflect::ShaderReflection;
use std::sync::Arc;

fn decline(binding: u32, detail: &'static str) -> DrawError {
    DrawError::DescriptorContract(DescriptorContractDecline::Resource { binding, detail })
}

pub(super) struct Prepared {
    stages: Vec<(bool, u32, GraphicsStagedTexture)>,
    pub images: Vec<GraphicsStorageImageResource>,
}

impl Prepared {
    pub(super) fn contains(&self, fragment: bool, binding: u32) -> bool {
        self.stages
            .iter()
            .any(|(f, b, _)| *f == fragment && *b == binding)
    }

    pub(super) fn writeback<M: HostMemory + HostOps>(
        &mut self,
        state: &mut DeviceState,
        host: &mut M,
        task: u32,
        images: Vec<Vec<u8>>,
    ) -> Result<(), DrawError> {
        if images.len() != self.stages.len() {
            return Err(decline(0, "graphics_storage_output_count"));
        }
        for ((_, binding, staged), bytes) in self.stages.iter_mut().zip(images) {
            staged
                .writeback(state, host, task, bytes)
                .map_err(|e| decline(*binding, e.reason()))?;
        }
        Ok(())
    }
}

pub(super) fn prepare<M: HostMemory + HostOps>(
    state: &mut DeviceState,
    host: &mut M,
    req: &DrawEncodeRequest,
    separate_fragment: bool,
    reflections: [&ShaderReflection; 2],
    words: [&mut Arc<Vec<u32>>; 2],
) -> Result<Prepared, DrawError> {
    let mut result = Prepared {
        stages: Vec::new(),
        images: Vec::new(),
    };
    let mut used_refs = Vec::new();
    for (stage, (reflection, words)) in reflections.into_iter().zip(words).enumerate() {
        let fragment = stage == 1;
        let offset = if fragment && separate_fragment {
            FRAG_SAMPLED_RESOURCE_BINDING_OFFSET
        } else {
            0
        };
        let binds = if fragment {
            &req.fragment_textures
        } else {
            &req.vertex_textures
        };
        for bind in binds {
            if bind.texture_ref == 0 || bind.index >= MAX_BIND_SLOTS {
                continue;
            }
            let base = TEXTURE_BINDING_BASE + bind.index;
            let binding = base + offset;
            // Reflection describes declared AIR arguments, which may have been
            // eliminated from SPIR-V. No global means no descriptor to stage.
            let Some(shader_format) = spirv_bind::image_format(words, binding) else {
                continue;
            };
            used_refs.push(bind.texture_ref);
            if !matches!(
                spirv_bind::reflected_compute_texture(reflection, base),
                ReflectedComputeTexture::Plain2d(ImageAccess::Storage)
            ) {
                continue;
            }
            let staged = compute_exec::stage_graphics_storage(
                state,
                host,
                req.task_id,
                bind.texture_ref,
                binding,
            )
            .map_err(|e| decline(binding, e.reason()))?;
            let native = crate::backend::vulkan::translate::pixel::storage_image(
                staged.texture.pixel_format,
            )
            .map_err(|_| decline(binding, "graphics_storage_native_format"))?;
            let access = spirv_bind::storage_image_access(words, binding);
            if !matches!(
                access,
                Some(
                    StorageImageAccess::WriteOnly
                        | StorageImageAccess::ReadOnly
                        | StorageImageAccess::ReadWrite
                )
            ) {
                return Err(decline(binding, "graphics_storage_access_unproven"));
            }
            let formatless = native == engine::StorageImageFormat::Bgra8Unorm
                && engine::supports_storage_image_write_without_format();
            let format =
                compute_exec::specialized_storage_image_format(native, shader_format, formatless)
                    .map_err(|reason| decline(binding, reason))?;
            // Do not inherit compute's historical degraded BGRA->RGBA fallback.
            // A colour write must land in the decoded guest channel order.
            if native == engine::StorageImageFormat::Bgra8Unorm && format == ImageFormat::Rgba8Unorm
            {
                return Err(decline(
                    binding,
                    "graphics_storage_bgra_requires_formatless_write",
                ));
            }
            if format == ImageFormat::Unknown && access != Some(StorageImageAccess::WriteOnly) {
                return Err(decline(
                    binding,
                    "graphics_storage_formatless_read_unsupported",
                ));
            }
            let concrete = if format == ImageFormat::Unknown {
                native
            } else {
                compute_exec::spirv_image_format_to_engine_storage(format)
                    .ok_or_else(|| decline(binding, "graphics_storage_specialized_format"))?
            };
            let words = Arc::make_mut(words);
            spirv_bind::specialize_image_formats(words, &[(binding, format)])
                .map_err(|_| decline(binding, "graphics_storage_specialize_failed"))?;
            if format == ImageFormat::Unknown {
                spirv_bind::ensure_storage_write_without_format_capability(words);
            }
            if result.stages.iter().any(|(_, _, old)| staged.overlaps(old)) {
                return Err(decline(binding, "graphics_storage_views_alias"));
            }
            result.images.push(GraphicsStorageImageResource {
                binding,
                format: concrete,
                width: staged.texture.width,
                height: staged.texture.height,
                bytes: staged.texture.bytes.clone(),
            });
            result.stages.push((fragment, binding, staged));
        }
    }
    if result.stages.is_empty() {
        return Ok(result);
    }
    // Independent transient images cannot implement a same-draw storage/read
    // feedback loop. Compare physical backing, not just unrelated object IDs.
    let mut other_refs = req
        .vertex_textures
        .iter()
        .chain(&req.fragment_textures)
        .filter(|b| b.texture_ref != 0 && used_refs.contains(&b.texture_ref))
        .map(|b| b.texture_ref)
        .collect::<Vec<_>>();
    other_refs.extend(
        req.colors
            .iter()
            .filter(|c| c.resident_texture_ref == 0)
            .map(|c| c.texture_ref),
    );
    other_refs.sort_unstable();
    other_refs.dedup();
    for texture_ref in other_refs {
        // Storage entries themselves were pairwise checked above. A ref also
        // bound for sampling/attachment is checked below, even if identical.
        let is_storage_only = req
            .vertex_textures
            .iter()
            .map(|b| (false, b))
            .chain(req.fragment_textures.iter().map(|b| (true, b)))
            .filter(|(_, b)| b.texture_ref == texture_ref)
            .all(|(f, b)| {
                result.contains(
                    f,
                    TEXTURE_BINDING_BASE
                        + b.index
                        + if f && separate_fragment {
                            FRAG_SAMPLED_RESOURCE_BINDING_OFFSET
                        } else {
                            0
                        },
                )
            })
            && !req.colors.iter().any(|c| c.texture_ref == texture_ref);
        if is_storage_only {
            continue;
        }
        let other = compute_exec::stage_graphics_storage(state, host, req.task_id, texture_ref, 0)
            .map_err(|_| decline(0, "graphics_storage_alias_backing_unproven"))?;
        if result.stages.iter().any(|(_, _, s)| s.overlaps(&other)) {
            return Err(decline(0, "graphics_storage_sample_or_attachment_alias"));
        }
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::contract::iosurface_pages::{PAGE_ENTRY_PFN_SHIFT, PAGE_ENTRY_VALID};
    use crate::contract::pixel_format::MTL_FORMAT_RGBA16_FLOAT;
    use crate::model::{DeviceId, PAGE_SHIFT_ARM64E};
    use crate::runtime::host::FakeHost;
    use crate::runtime::metal_draw::{ColorRtRequest, TextureBind};
    use metal2vulkan::reflect::{
        DescriptorLocation, ResourceBinding, ResourceKind, ShaderStage, REFLECTION_VERSION,
    };

    fn reflection() -> ShaderReflection {
        ShaderReflection {
            reflection_version: REFLECTION_VERSION,
            stage: ShaderStage::Fragment,
            entry_point: None,
            bindings: vec![ResourceBinding {
                kind: ResourceKind::StorageImage,
                metal_index: 3,
                descriptor: Some(DescriptorLocation {
                    set: 0,
                    binding: 35,
                }),
                param_index: None,
                address_space: None,
                declared_size: None,
                type_layout: None,
                type_name: None,
                embedded_source: None,
                access: None,
                static_sampler: None,
                texture_shape: Some(metal2vulkan::meta::texture_shape_from_name(
                    "texture2d<float, write>",
                )),
            }],
            vertex_attributes: vec![],
            varyings: vec![],
            render_targets: vec![],
            depth_members: vec![],
            stencil_members: vec![],
            local_size: None,
            vertex_builtins: None,
            imageblock_layouts: vec![],
            datalayout: None,
            function_constants: vec![],
        }
    }

    // Parser-only synthetic use graph. GPU tests separately compile complete
    // GLSL programs and validate real pixel output; no guest bytes are fixtures.
    fn words(binding: u32) -> Arc<Vec<u32>> {
        let mut words = vec![0x0723_0203, 0x10000, 0, 32, 0];
        for (op, a) in [
            (71, vec![3, 33, binding]),
            (71, vec![3, 34, 0]),
            (25, vec![1, 20, 1, 0, 0, 0, 2, 1]),
            (32, vec![2, 0, 1]),
            (59, vec![2, 3, 0]),
            (61, vec![1, 4, 3]),
            (99, vec![4, 5, 6]),
        ] {
            words.push(((a.len() as u32 + 1) << 16) | op);
            words.extend(a);
        }
        Arc::new(words)
    }

    fn fixture() -> (DeviceState, FakeHost) {
        let mut state = DeviceState::new(DeviceId(1), PAGE_SHIFT_ARM64E);
        let mut host = FakeHost::new();
        for id in [3, 4] {
            let pfn = id * 16;
            host.map_range((pfn as u64) << PAGE_SHIFT_ARM64E, 0x4000, 0x5a);
            state.map_surface(id);
            state.mappings.get_mut(&id).unwrap().page_entries =
                vec![(pfn << PAGE_ENTRY_PFN_SHIFT) | PAGE_ENTRY_VALID];
            state.set_mapping_geom(id, 4, 4, MTL_FORMAT_RGBA16_FLOAT);
        }
        (state, host)
    }

    #[test]
    fn graphics_storage_runtime_routes_both_stages_relocates_and_writes_native_bytes() {
        for fragment in [false, true] {
            for separate in [false, true] {
                let (mut state, mut host) = fixture();
                let binding = 35 + if fragment && separate { 128 } else { 0 };
                let mut req = DrawEncodeRequest::default();
                if fragment {
                    req.fragment_textures.push(TextureBind {
                        index: 3,
                        texture_ref: 3,
                    });
                } else {
                    req.vertex_textures.push(TextureBind {
                        index: 3,
                        texture_ref: 3,
                    });
                }
                req.colors.push(ColorRtRequest {
                    texture_ref: 4,
                    mapping_id: 4,
                    ..Default::default()
                });
                let reflection = reflection();
                let mut v = words(35);
                let mut f = words(binding);
                let mut prepared = prepare(
                    &mut state,
                    &mut host,
                    &req,
                    separate,
                    [&reflection, &reflection],
                    [&mut v, &mut f],
                )
                .unwrap();
                assert_eq!(prepared.images.len(), 1);
                assert_eq!(prepared.images[0].binding, binding);
                assert_eq!(
                    prepared.images[0].format,
                    engine::StorageImageFormat::Rgba16Float
                );
                assert_eq!(
                    spirv_bind::image_format(if fragment { &f } else { &v }, binding),
                    Some(ImageFormat::Rgba16Float)
                );
                prepared
                    .writeback(&mut state, &mut host, 0, vec![vec![0x12; 128]])
                    .unwrap();
                // The descriptor-free IOSurface fixture uses the contract's
                // aligned row stride, not tight host staging. Check all four
                // rows and retain every padding/neighbor byte.
                let pitch = crate::contract::iosurface_pages::ROW_BYTES_ALIGN as usize;
                let mut got = vec![0; 0x4000];
                host.read_gpa(48 << PAGE_SHIFT_ARM64E, &mut got).unwrap();
                for (offset, byte) in got.into_iter().enumerate() {
                    let expected = if offset / pitch < 4 && offset % pitch < 32 {
                        0x12
                    } else {
                        0x5a
                    };
                    assert_eq!(byte, expected, "guest byte {offset}");
                }
            }
        }
    }

    #[test]
    fn graphics_storage_runtime_refuses_attachment_alias_before_gpu() {
        let (mut state, mut host) = fixture();
        let req = DrawEncodeRequest {
            fragment_textures: vec![TextureBind {
                index: 3,
                texture_ref: 3,
            }],
            colors: vec![ColorRtRequest {
                texture_ref: 3,
                mapping_id: 3,
                ..Default::default()
            }],
            ..Default::default()
        };
        let reflection = reflection();
        let mut v = words(35);
        let mut f = words(163);
        let error = prepare(
            &mut state,
            &mut host,
            &req,
            true,
            [&reflection, &reflection],
            [&mut v, &mut f],
        )
        .err()
        .unwrap();
        assert_eq!(
            error,
            decline(0, "graphics_storage_sample_or_attachment_alias")
        );
    }
}
