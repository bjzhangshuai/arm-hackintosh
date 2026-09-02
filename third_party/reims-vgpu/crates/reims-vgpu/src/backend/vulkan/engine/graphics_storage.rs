//! Synchronous native-texel storage images in vertex/fragment draws.
//!
//! Pool slots stay with the submission's cleanup until its fence retires. The
//! image is never a guest-memory import, sampled alias, or colour attachment.

use super::{
    context::DeviceContext,
    counters::EngineCounters,
    descriptor_contract::DescriptorContractDecline as D,
    pools::{BufferSlot, ResourcePools, StorageImageKey, StorageImageSlot},
    types::{DrawError, GraphicsStorageImageResource, StorageImageFormat},
    vk_call::VkOp,
};
use ash::vk;

pub(super) fn spirv_format(format: StorageImageFormat) -> Option<u32> {
    use StorageImageFormat::*;
    // SPIR-V Image Format enumerants (Khronos core grammar).
    Some(match format {
        Rgba32Float => 1,
        Rgba16Float => 2,
        R32Float => 3,
        Rgba8Unorm => 4,
        Rg16Float => 7,
        R16Float => 9,
        Rg8Unorm => 13,
        R8Unorm => 15,
        Rgba8Sint => 23,
        R32Sint => 24,
        Rgba32Uint => 30,
        Rgba16Uint => 31,
        Rgba8Uint => 32,
        R32Uint => 33,
        Bgra8Unorm | Rgb9e5Ufloat => return None,
    })
}

pub(super) fn validate(r: &GraphicsStorageImageResource) -> Result<(), D> {
    let invalid = |detail| D::Resource {
        binding: r.binding,
        detail,
    };
    if r.width == 0 || r.height == 0 {
        return Err(invalid("zero storage image geometry"));
    }
    let expected = (r.width as usize)
        .checked_mul(r.height as usize)
        .and_then(|n| n.checked_mul(r.format.bytes_per_texel()))
        .ok_or_else(|| invalid("storage image byte extent overflow"))?;
    if r.bytes.len() != expected {
        return Err(invalid(
            "storage image seed must contain exact tight native texels",
        ));
    }
    if r.format == StorageImageFormat::Rgb9e5Ufloat {
        return Err(invalid("sample-only storage image format"));
    }
    Ok(())
}

pub(super) fn numeric_class(format: StorageImageFormat) -> u8 {
    use StorageImageFormat::*;
    match format {
        Rgba16Uint | Rgba8Uint | Rgba32Uint | R32Uint => 1,
        Rgba8Sint | R32Sint => 2,
        _ => 0,
    }
}

pub(super) struct Prepared {
    pub binding: u32,
    image: StorageImageSlot,
    seed: BufferSlot,
    readback: BufferSlot,
    len: u64,
}

impl Prepared {
    pub(super) unsafe fn acquire(
        ctx: &DeviceContext,
        pools: &mut ResourcePools,
        counters: &EngineCounters,
        r: &GraphicsStorageImageResource,
    ) -> Result<Self, DrawError> {
        validate(r).map_err(DrawError::DescriptorContract)?;
        let fail = |detail| {
            DrawError::DescriptorContract(D::Resource {
                binding: r.binding,
                detail,
            })
        };
        let usage = vk::ImageUsageFlags::STORAGE
            | vk::ImageUsageFlags::TRANSFER_SRC
            | vk::ImageUsageFlags::TRANSFER_DST;
        let props = unsafe {
            ctx.instance.get_physical_device_image_format_properties(
                ctx.pd,
                r.format.vk_format(),
                vk::ImageType::TYPE_2D,
                vk::ImageTiling::OPTIMAL,
                usage,
                vk::ImageCreateFlags::empty(),
            )
        }
        .map_err(|_| fail("native storage image usage unsupported"))?;
        if r.width > props.max_extent.width || r.height > props.max_extent.height {
            return Err(fail("native storage image exceeds device extent"));
        }
        let image = unsafe {
            pools.acquire_storage_image(
                ctx,
                StorageImageKey {
                    width: r.width,
                    height: r.height,
                    format: r.format,
                    sampled_only: false,
                },
                counters,
            )?
        };
        let len = r.bytes.len() as u64;
        let seed = unsafe {
            pools.acquire_staging(ctx, len, vk::BufferUsageFlags::TRANSFER_SRC, counters)?
        };
        unsafe {
            pools.write_staging(ctx, &seed, &r.bytes)?;
        }
        let readback = unsafe { pools.acquire_readback_extra(ctx, len, counters)? };
        Ok(Self {
            binding: r.binding,
            image,
            seed,
            readback,
            len,
        })
    }

    pub(super) fn descriptor(&self) -> vk::DescriptorImageInfo {
        vk::DescriptorImageInfo::default()
            .image_view(self.image.view)
            .image_layout(vk::ImageLayout::GENERAL)
    }

    fn copy_region(&self) -> vk::BufferImageCopy {
        vk::BufferImageCopy::default()
            .image_subresource(super::color_subresource_layers())
            .image_extent(vk::Extent3D {
                width: self.image.key.width,
                height: self.image.key.height,
                depth: 1,
            })
    }

    pub(super) unsafe fn before_draw(&self, ctx: &DeviceContext, cb: vk::CommandBuffer) {
        let barrier = |old, new, src, dst| {
            vk::ImageMemoryBarrier::default()
                .image(self.image.image)
                .subresource_range(super::color_subresource_range())
                .src_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
                .dst_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
                .old_layout(old)
                .new_layout(new)
                .src_access_mask(src)
                .dst_access_mask(dst)
        };
        unsafe {
            ctx.device.cmd_pipeline_barrier(
                cb,
                vk::PipelineStageFlags::TOP_OF_PIPE,
                vk::PipelineStageFlags::TRANSFER,
                vk::DependencyFlags::empty(),
                &[],
                &[],
                &[barrier(
                    vk::ImageLayout::UNDEFINED,
                    vk::ImageLayout::TRANSFER_DST_OPTIMAL,
                    vk::AccessFlags::empty(),
                    vk::AccessFlags::TRANSFER_WRITE,
                )],
            );
            ctx.device.cmd_copy_buffer_to_image(
                cb,
                self.seed.buffer,
                self.image.image,
                vk::ImageLayout::TRANSFER_DST_OPTIMAL,
                &[self.copy_region()],
            );
            ctx.device.cmd_pipeline_barrier(
                cb,
                vk::PipelineStageFlags::TRANSFER,
                vk::PipelineStageFlags::VERTEX_SHADER | vk::PipelineStageFlags::FRAGMENT_SHADER,
                vk::DependencyFlags::empty(),
                &[],
                &[],
                &[barrier(
                    vk::ImageLayout::TRANSFER_DST_OPTIMAL,
                    vk::ImageLayout::GENERAL,
                    vk::AccessFlags::TRANSFER_WRITE,
                    vk::AccessFlags::SHADER_READ | vk::AccessFlags::SHADER_WRITE,
                )],
            );
        }
    }

    pub(super) unsafe fn after_draw(&self, ctx: &DeviceContext, cb: vk::CommandBuffer) {
        let barrier = vk::ImageMemoryBarrier::default()
            .image(self.image.image)
            .subresource_range(super::color_subresource_range())
            .src_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
            .dst_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
            .old_layout(vk::ImageLayout::GENERAL)
            .new_layout(vk::ImageLayout::TRANSFER_SRC_OPTIMAL)
            .src_access_mask(vk::AccessFlags::SHADER_READ | vk::AccessFlags::SHADER_WRITE)
            .dst_access_mask(vk::AccessFlags::TRANSFER_READ);
        unsafe {
            ctx.device.cmd_pipeline_barrier(
                cb,
                vk::PipelineStageFlags::VERTEX_SHADER | vk::PipelineStageFlags::FRAGMENT_SHADER,
                vk::PipelineStageFlags::TRANSFER,
                vk::DependencyFlags::empty(),
                &[],
                &[],
                &[barrier],
            );
            ctx.device.cmd_copy_image_to_buffer(
                cb,
                self.image.image,
                vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
                self.readback.buffer,
                &[self.copy_region()],
            );
            let ready = vk::BufferMemoryBarrier::default()
                .buffer(self.readback.buffer)
                .offset(0)
                .size(self.len)
                .src_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
                .dst_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
                .src_access_mask(vk::AccessFlags::TRANSFER_WRITE)
                .dst_access_mask(vk::AccessFlags::HOST_READ);
            ctx.device.cmd_pipeline_barrier(
                cb,
                vk::PipelineStageFlags::TRANSFER,
                vk::PipelineStageFlags::HOST,
                vk::DependencyFlags::empty(),
                &[],
                &[ready],
                &[],
            );
        }
    }

    /// Called only after this submission's fence signaled, before its pool
    /// slots can be recycled by a later entry.
    pub(super) unsafe fn read(&self, ctx: &DeviceContext) -> Result<Vec<u8>, DrawError> {
        unsafe {
            super::pools::read_back_slot(
                ctx,
                &self.readback,
                self.len,
                VkOp::ExecMapReadback,
                VkOp::ExecInvalidateReadback,
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn graphics_storage_requires_exact_native_extent() {
        for format in [
            StorageImageFormat::R8Unorm,
            StorageImageFormat::Rg16Float,
            StorageImageFormat::Rgba16Float,
            StorageImageFormat::Rgba32Float,
        ] {
            let len = 6 * format.bytes_per_texel();
            let mut r = GraphicsStorageImageResource {
                binding: 163,
                format,
                width: 3,
                height: 2,
                bytes: vec![0; len],
            };
            assert!(validate(&r).is_ok());
            r.bytes.pop();
            assert!(validate(&r).is_err());
            r.bytes.resize(len + 1, 0);
            assert!(validate(&r).is_err());
            r.bytes.resize(len, 0);
            r.width = 0;
            assert!(validate(&r).is_err());
            r.width = u32::MAX;
            r.height = u32::MAX;
            assert!(validate(&r).is_err());
        }
    }
}
