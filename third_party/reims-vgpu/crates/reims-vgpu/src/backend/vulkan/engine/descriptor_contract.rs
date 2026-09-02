//! Validate the shader/resource seam before any Vulkan work is recorded.
//!
//! A layout built from the supplied resources is not evidence that it matches
//! the shader. In particular, a storage image cannot use a sampled descriptor,
//! and an absent binding is not a valid Vulkan null descriptor. Keep these
//! failures out of the driver. This does not implement missing resources or
//! replace spirv-val. SPIR-V 1.4+ supplies the entry's complete global interface;
//! for older modules the check conservatively covers all descriptor globals.

use std::collections::{BTreeMap, HashMap, HashSet};

use ash::vk;

use super::types::{DrawRequest, COLOR_INPUT_BINDING};
use crate::observe::Decline;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DescriptorContractDecline {
    Limit {
        name: &'static str,
        requested: u32,
        supported: u32,
    },
    Malformed {
        word: usize,
    },
    Missing {
        stage: u32,
        set: u32,
        binding: u32,
    },
    Type {
        stage: u32,
        binding: u32,
        shader: vk::DescriptorType,
        resource: vk::DescriptorType,
    },
    Unsupported {
        stage: u32,
        variable: u32,
        detail: &'static str,
    },
    ImageShape {
        stage: u32,
        binding: u32,
        dim: u32,
        arrayed: u32,
        multisampled: u32,
    },
    Duplicate {
        binding: u32,
    },
    Resource {
        binding: u32,
        detail: &'static str,
    },
}

impl Decline for DescriptorContractDecline {
    fn slug(&self) -> &'static str {
        match self {
            Self::Limit { .. } => "vk_draw_descriptor_limit",
            Self::Malformed { .. } => "vk_draw_descriptor_malformed",
            Self::Missing { .. } => "vk_draw_descriptor_missing",
            Self::Type { .. } => "vk_draw_descriptor_type",
            Self::Unsupported { .. } => "vk_draw_descriptor_unsupported",
            Self::ImageShape { .. } => "vk_draw_descriptor_image_shape",
            Self::Duplicate { .. } => "vk_draw_descriptor_duplicate",
            Self::Resource { .. } => "vk_draw_descriptor_resource",
        }
    }
    fn fields(&self) -> Vec<(&'static str, String)> {
        vec![("contract", format!("{self:?}"))]
    }
}
crate::observe::decline_display!(DescriptorContractDecline);

#[derive(Clone, Copy)]
struct Supplied {
    ty: vk::DescriptorType,
    shape: Option<(u32, u32, u32)>,
    storage_format: Option<super::types::StorageImageFormat>,
}

fn inventory(req: &DrawRequest) -> Result<BTreeMap<u32, Supplied>, DescriptorContractDecline> {
    if req.secondary_color_inputs & 1 != 0
        || (req.secondary_color_inputs as u16) >> (req.secondary_targets.len().min(7) + 1) != 0
    {
        return Err(DescriptorContractDecline::Unsupported {
            stage: 4,
            variable: 0,
            detail: "framebuffer-fetch slot is not attached (slot 0 uses color_input)",
        });
    }
    let mut result = BTreeMap::new();
    let mut add = |binding, ty, shape| {
        if result
            .insert(
                binding,
                Supplied {
                    ty,
                    shape,
                    storage_format: None,
                },
            )
            .is_some()
        {
            return Err(DescriptorContractDecline::Duplicate { binding });
        }
        Ok(())
    };
    for buffer in &req.storage_buffers {
        add(buffer.binding, vk::DescriptorType::STORAGE_BUFFER, None)?;
    }
    for image in &req.sampled_images {
        // SPIR-V Dim: 1D=0, 2D=1, 3D=2, Cube=3. Descriptor arrays
        // (OpTypeArray) and arrayed image views are distinct contracts.
        let dim = if image.one_dim {
            0
        } else if image.volume {
            2
        } else if image.cube {
            3
        } else {
            1
        };
        add(
            image.binding,
            vk::DescriptorType::SAMPLED_IMAGE,
            Some((dim, u32::from(image.arrayed), 0)),
        )?;
    }
    for sampler in &req.samplers {
        add(sampler.binding, vk::DescriptorType::SAMPLER, None)?;
    }
    for image in &req.storage_images {
        super::graphics_storage::validate(image)?;
        add(
            image.binding,
            vk::DescriptorType::STORAGE_IMAGE,
            Some((1, 0, 0)),
        )?;
    }
    if req.color_input {
        add(
            COLOR_INPUT_BINDING,
            vk::DescriptorType::INPUT_ATTACHMENT,
            Some((6, 0, 0)),
        )?;
    }
    for i in 1..8 {
        if req.secondary_color_inputs & (1 << i) != 0 {
            add(
                COLOR_INPUT_BINDING + i,
                vk::DescriptorType::INPUT_ATTACHMENT,
                Some((6, 0, 0)),
            )?;
        }
    }
    for image in &req.storage_images {
        result
            .get_mut(&image.binding)
            .expect("inserted storage binding")
            .storage_format = Some(image.format);
    }
    Ok(result)
}

fn check_module(
    words: &[u32],
    stage: u32,
    supplied: &BTreeMap<u32, Supplied>,
) -> Result<(), DescriptorContractDecline> {
    use DescriptorContractDecline as D;
    if words.len() < 5 || words[0] != 0x0723_0203 || words[3] == 0 {
        return Err(D::Malformed { word: 0 });
    }
    let mut types = HashMap::new();
    let mut pointers = HashMap::new();
    let mut variables = Vec::new();
    let mut decorations: HashMap<u32, (Option<u32>, Option<u32>)> = HashMap::new();
    let mut blocks = HashMap::new();
    let mut input_indices = HashMap::new();
    let mut interface = HashSet::new();
    let mut capabilities = HashSet::new();
    let mut found_entry = false;
    let mut at = 5;
    while at < words.len() {
        let wc = (words[at] >> 16) as usize;
        let op = words[at] & 0xffff;
        if wc == 0 || wc > words.len() - at {
            return Err(D::Malformed { word: at });
        }
        let a = &words[at + 1..at + wc];
        let min = match op {
            15 => 3,
            17 => 1,
            21 => 3,
            22 => 2,
            25 => 8,
            26 | 30 => 1,
            27 | 29 => 2,
            28 | 32 | 59 => 3,
            71 => 2,
            _ => 0,
        };
        if a.len() < min {
            return Err(D::Malformed { word: at });
        }
        match op {
            15 => {
                let end = a[2..]
                    .iter()
                    .position(|v| v.to_le_bytes().contains(&0))
                    .map(|n| n + 2)
                    .ok_or(D::Malformed { word: at })?;
                let name: Vec<u8> = a[2..=end]
                    .iter()
                    .flat_map(|v| v.to_le_bytes())
                    .take_while(|v| *v != 0)
                    .collect();
                if a[0] == stage && name == b"main" {
                    found_entry = true;
                    interface.extend(a[end + 1..].iter().copied());
                }
            }
            17 => {
                capabilities.insert(a[0]);
            }
            21 | 22 | 25..=30 => {
                types.insert(a[0], (op, a));
            }
            32 => {
                pointers.insert(a[0], (a[1], a[2]));
            }
            59 if matches!(a[2], 0 | 2 | 12) => {
                variables.push((a[0], a[1], a[2]));
            }
            71 if matches!(a[1], 33 | 34) => {
                let value = *a.get(2).ok_or(D::Malformed { word: at })?;
                let entry = decorations.entry(a[0]).or_default();
                let slot = if a[1] == 33 {
                    &mut entry.1
                } else {
                    &mut entry.0
                };
                if slot.replace(value).is_some_and(|old| old != value) {
                    return Err(D::Malformed { word: at });
                }
            }
            71 if matches!(a[1], 2 | 3) => {
                blocks.insert(a[0], a[1]);
            }
            71 if a[1] == 43 => {
                input_indices.insert(a[0], *a.get(2).ok_or(D::Malformed { word: at })?);
            }
            _ => {}
        }
        at += wc;
    }
    if !found_entry {
        return Err(D::Unsupported {
            stage,
            variable: 0,
            detail: "missing main entry point",
        });
    }
    for (pointer, variable, storage) in variables {
        if words[1] >= 0x0001_0400 && !interface.contains(&variable) {
            continue;
        }
        let unsupported = |detail| D::Unsupported {
            stage,
            variable,
            detail,
        };
        let &(pointer_storage, pointee) = pointers
            .get(&pointer)
            .ok_or_else(|| unsupported("missing pointer type"))?;
        if pointer_storage != storage {
            return Err(unsupported("pointer storage class mismatch"));
        }
        let &(set, binding) = decorations
            .get(&variable)
            .ok_or_else(|| unsupported("missing descriptor decorations"))?;
        let set = set.ok_or_else(|| unsupported("missing descriptor set"))?;
        let binding = binding.ok_or_else(|| unsupported("missing binding"))?;
        let &(op, a) = types
            .get(&pointee)
            .ok_or_else(|| unsupported("missing descriptor type"))?;
        let shader = match (storage, op) {
            (12, 30) if blocks.get(&pointee) == Some(&2) => vk::DescriptorType::STORAGE_BUFFER,
            (2, 30) if blocks.get(&pointee) == Some(&3) => vk::DescriptorType::STORAGE_BUFFER,
            (2, 30) if blocks.get(&pointee) == Some(&2) => vk::DescriptorType::UNIFORM_BUFFER,
            (0, 26) => vk::DescriptorType::SAMPLER,
            (0, 27) => vk::DescriptorType::COMBINED_IMAGE_SAMPLER,
            (0, 25) if a[2] == 6 && a[6] == 2 => vk::DescriptorType::INPUT_ATTACHMENT,
            (0, 25) if a[2] == 5 && a[6] == 1 => vk::DescriptorType::UNIFORM_TEXEL_BUFFER,
            (0, 25) if a[2] == 5 && a[6] == 2 => vk::DescriptorType::STORAGE_TEXEL_BUFFER,
            (0, 25) if a[6] == 1 => vk::DescriptorType::SAMPLED_IMAGE,
            (0, 25) if a[6] == 2 => vk::DescriptorType::STORAGE_IMAGE,
            (_, 28 | 29) => return Err(unsupported("descriptor arrays require array resources")),
            _ => return Err(unsupported("descriptor type not supported")),
        };
        let resource = supplied
            .get(&binding)
            .filter(|_| set == 0)
            .ok_or(D::Missing {
                stage,
                set,
                binding,
            })?;
        if shader != resource.ty {
            return Err(D::Type {
                stage,
                binding,
                shader,
                resource: resource.ty,
            });
        }
        if shader == vk::DescriptorType::INPUT_ATTACHMENT
            && input_indices
                .get(&variable)
                .and_then(|i| COLOR_INPUT_BINDING.checked_add(*i))
                != Some(binding)
        {
            return Err(unsupported(
                "input attachment index does not match its color slot",
            ));
        }
        if op == 25 && resource.shape != Some((a[2], a[4], a[5])) {
            return Err(D::ImageShape {
                stage,
                binding,
                dim: a[2],
                arrayed: a[4],
                multisampled: a[5],
            });
        }
        if let Some(format) = resource.storage_format {
            let numeric_class = match types.get(&a[1]) {
                Some((22, _)) => 0,
                Some((21, scalar)) if scalar[2] == 0 => 1,
                Some((21, scalar)) if scalar[2] == 1 => 2,
                _ => return Err(unsupported("storage sampled type is not scalar numeric")),
            };
            if numeric_class != super::graphics_storage::numeric_class(format) {
                return Err(unsupported(
                    "storage image sampled type does not match native view",
                ));
            }
            // A concretely formatted shader must agree with the native image
            // view. Format-less access is separately capability/access checked.
            if a[7] != 0 && super::graphics_storage::spirv_format(format) != Some(a[7]) {
                return Err(unsupported(
                    "storage image format does not match native view",
                ));
            }
            if a[7] == 0
                && !matches!(
                    crate::runtime::spirv_bind::storage_image_access(words, binding),
                    Some(crate::runtime::spirv_bind::StorageImageAccess::WriteOnly)
                )
            {
                return Err(unsupported(
                    "format-less graphics storage must be proven write-only",
                ));
            }
            if a[7] == 0 && !capabilities.contains(&56) {
                return Err(unsupported("format-less write capability is undeclared"));
            }
        }
    }
    Ok(())
}

pub(super) fn check(req: &DrawRequest) -> Result<(), DescriptorContractDecline> {
    let supplied = inventory(req)?;
    check_module(&req.vert_spirv, 0, &supplied)?;
    check_module(&req.frag_spirv, 4, &supplied)
}

pub(super) fn check_limits(
    req: &DrawRequest,
    limits: &vk::PhysicalDeviceLimits,
) -> Result<(), DescriptorContractDecline> {
    let mask = req.secondary_color_inputs | u8::from(req.color_input);
    // VkSubpassDescription's inputAttachmentCount includes unused holes;
    // descriptor-set accounting counts only the descriptors actually bound.
    for (name, requested, supported) in [
        (
            "maxColorAttachments",
            req.secondary_targets
                .len()
                .saturating_add(1)
                .min(u32::MAX as usize) as u32,
            limits.max_color_attachments,
        ),
        (
            "maxPerStageDescriptorInputAttachments",
            u8::BITS - mask.leading_zeros(),
            limits.max_per_stage_descriptor_input_attachments,
        ),
        (
            "maxDescriptorSetInputAttachments",
            mask.count_ones(),
            limits.max_descriptor_set_input_attachments,
        ),
        (
            "maxPerStageDescriptorStorageImages",
            req.storage_images.len() as u32,
            limits.max_per_stage_descriptor_storage_images,
        ),
        (
            "maxDescriptorSetStorageImages",
            req.storage_images.len() as u32,
            limits.max_descriptor_set_storage_images,
        ),
    ] {
        if requested > supported {
            return Err(DescriptorContractDecline::Limit {
                name,
                requested,
                supported,
            });
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sparse_input_indices_and_dense_descriptors_obey_device_limits() {
        let mut req = DrawRequest {
            secondary_color_inputs: 128,
            ..Default::default()
        };
        let mut limits = vk::PhysicalDeviceLimits {
            max_color_attachments: 8,
            max_per_stage_descriptor_input_attachments: 7,
            max_descriptor_set_input_attachments: 1,
            ..Default::default()
        };
        assert!(matches!(
            check_limits(&req, &limits),
            Err(DescriptorContractDecline::Limit {
                requested: 8,
                supported: 7,
                ..
            })
        ));
        limits.max_per_stage_descriptor_input_attachments = 8;
        assert_eq!(check_limits(&req, &limits), Ok(()));
        req.color_input = true;
        assert!(matches!(
            check_limits(&req, &limits),
            Err(DescriptorContractDecline::Limit {
                name: "maxDescriptorSetInputAttachments",
                requested: 2,
                ..
            })
        ));
        req.secondary_color_inputs = 0;
        req.color_input = false;
        limits.max_color_attachments = 0;
        assert!(matches!(
            check_limits(&req, &limits),
            Err(DescriptorContractDecline::Limit {
                name: "maxColorAttachments",
                ..
            })
        ));
    }

    fn module(
        stage: u32,
        sampled: u32,
        dim: u32,
        arrayed: u32,
        ms: u32,
        binding: u32,
        set: u32,
    ) -> Vec<u32> {
        let mut w = vec![0x0723_0203, 0x0001_0400, 0, 40, 0];
        for (op, a) in [
            (15, vec![stage, 10, 0x6e69616d, 0, 3]),
            (71, vec![3, 33, binding]),
            (71, vec![3, 34, set]),
            (25, vec![1, 20, dim, 0, arrayed, ms, sampled, 0]),
            (32, vec![2, 0, 1]),
            (59, vec![2, 3, 0]),
        ] {
            w.push(((a.len() as u32 + 1) << 16) | op);
            w.extend(a);
        }
        w
    }
    fn supplied(binding: u32) -> BTreeMap<u32, Supplied> {
        BTreeMap::from([(
            binding,
            Supplied {
                ty: vk::DescriptorType::SAMPLED_IMAGE,
                shape: Some((1, 0, 0)),
                storage_format: None,
            },
        )])
    }
    #[test]
    fn missing_and_storage_as_sampled_reject_for_both_stages_and_arbitrary_bindings() {
        for stage in [0, 4] {
            for binding in [0, 35, 161, 163, 1024] {
                assert!(matches!(
                    check_module(
                        &module(stage, 1, 1, 0, 0, binding, 0),
                        stage,
                        &BTreeMap::new()
                    ),
                    Err(DescriptorContractDecline::Missing { .. })
                ));
                assert!(matches!(
                    check_module(
                        &module(stage, 2, 1, 0, 0, binding, 0),
                        stage,
                        &supplied(binding)
                    ),
                    Err(DescriptorContractDecline::Type {
                        shader: vk::DescriptorType::STORAGE_IMAGE,
                        ..
                    })
                ));
                assert_eq!(
                    check_module(
                        &module(stage, 1, 1, 0, 0, binding, 0),
                        stage,
                        &supplied(binding)
                    ),
                    Ok(())
                );
            }
        }
    }
    #[test]
    fn shape_and_set_mismatches_reject() {
        for (dim, arrayed, ms) in [(0, 0, 0), (2, 0, 0), (3, 0, 0), (1, 1, 0), (1, 0, 1)] {
            assert!(matches!(
                check_module(&module(4, 1, dim, arrayed, ms, 32, 0), 4, &supplied(32)),
                Err(DescriptorContractDecline::ImageShape { .. })
            ));
        }
        assert!(matches!(
            check_module(&module(4, 1, 1, 0, 0, 32, 1), 4, &supplied(32)),
            Err(DescriptorContractDecline::Missing { set: 1, .. })
        ));
    }
    #[test]
    fn unsupported_arrays_never_alias_single_image() {
        let mut w = module(4, 1, 1, 0, 0, 32, 0);
        let pointer = w.iter().position(|v| *v == (4 << 16 | 32)).unwrap();
        w[pointer + 3] = 4;
        w.extend([(4 << 16) | 28, 4, 1, 5]);
        assert!(matches!(
            check_module(&w, 4, &supplied(32)),
            Err(DescriptorContractDecline::Unsupported {
                detail: "descriptor arrays require array resources",
                ..
            })
        ));
    }
    #[test]
    fn input_attachment_and_texel_buffers_are_not_sampled_images() {
        for (dim, sampled, ty) in [
            (6, 2, vk::DescriptorType::INPUT_ATTACHMENT),
            (5, 1, vk::DescriptorType::UNIFORM_TEXEL_BUFFER),
            (5, 2, vk::DescriptorType::STORAGE_TEXEL_BUFFER),
        ] {
            assert!(
                matches!(check_module(&module(4, sampled, dim, 0, 0, 32, 0), 4, &supplied(32)), Err(DescriptorContractDecline::Type { shader, .. }) if shader == ty)
            );
        }
    }
    #[test]
    fn unused_14_global_is_not_a_required_binding() {
        let mut w = module(4, 1, 1, 0, 0, 32, 0);
        w[5] = (5 << 16) | 15;
        w.remove(10);
        assert_eq!(check_module(&w, 4, &BTreeMap::new()), Ok(()));
    }
    #[test]
    fn malformed_streams_fail_without_panicking_or_allocating_by_id_bound() {
        let w = module(4, 1, 1, 0, 0, 32, 0);
        for n in 0..5 {
            assert!(check_module(&w[..n], 4, &supplied(32)).is_err());
        }
        let mut at = 5;
        while at < w.len() {
            let end = at + (w[at] >> 16) as usize;
            for n in at + 1..end {
                assert!(
                    check_module(&w[..n], 4, &supplied(32)).is_err(),
                    "truncated instruction {n}"
                );
            }
            at = end;
        }
        let mut bad = w.clone();
        bad[5] = 0;
        assert!(check_module(&bad, 4, &supplied(32)).is_err());
        let mut large_bound = w;
        large_bound[3] = u32::MAX;
        assert_eq!(check_module(&large_bound, 4, &supplied(32)), Ok(()));
    }
}
