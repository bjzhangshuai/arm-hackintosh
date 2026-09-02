//! Feature preflight for translated shader modules, before calling the driver.
//!
//! This is not a replacement for spirv-val. It covers the optional feature
//! contracts used by the AIR backend: variable pointers, demote, and writable
//! storage in graphics stages. Numeric values below are SPIR-V core grammar
//! opcodes, storage classes, decorations and capabilities (Khronos SPIRV-Headers).

use std::collections::{HashMap, HashSet};

use crate::backend::vulkan::caps::device_features::DeviceFeatures;
use crate::observe::Decline;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShaderFeature {
    VariablePointersStorageBuffer,
    VariablePointers,
    DemoteToHelperInvocation,
    VertexPipelineStoresAndAtomics,
    FragmentStoresAndAtomics,
    StorageImageWriteWithoutFormat,
    StorageImageReadWithoutFormat,
    StorageImageExtendedFormats,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShaderContractDecline {
    Malformed { word: usize },
    MissingFeature { feature: ShaderFeature },
}

impl Decline for ShaderContractDecline {
    fn slug(&self) -> &'static str {
        match self {
            Self::Malformed { .. } => "shader_feature_contract_malformed",
            Self::MissingFeature { .. } => "shader_feature_not_enabled",
        }
    }

    fn fields(&self) -> Vec<(&'static str, String)> {
        match self {
            Self::Malformed { word } => vec![("word", word.to_string())],
            Self::MissingFeature { feature } => vec![("feature", format!("{feature:?}"))],
        }
    }
}

crate::observe::decline_display!(ShaderContractDecline);

fn require(enabled: bool, feature: ShaderFeature) -> Result<(), ShaderContractDecline> {
    if enabled {
        Ok(())
    } else {
        Err(ShaderContractDecline::MissingFeature { feature })
    }
}

pub(super) fn check(words: &[u32], features: &DeviceFeatures) -> Result<(), ShaderContractDecline> {
    if words.len() < 5 || words[0] != 0x0723_0203 {
        return Err(ShaderContractDecline::Malformed { word: 0 });
    }
    let mut stages = HashSet::new();
    let mut capabilities = HashSet::new();
    let mut variables = Vec::new();
    let mut pointees = HashMap::new();
    let mut arrays = HashMap::new();
    let mut struct_members = HashMap::new();
    let mut storage_images = HashSet::new();
    let mut buffer_blocks = HashSet::new();
    let mut nonwritable = HashSet::new();
    let mut nonwritable_members = HashSet::new();
    let mut at = 5;
    while at < words.len() {
        let count = (words[at] >> 16) as usize;
        let opcode = words[at] & 0xffff;
        if count == 0 || count > words.len() - at {
            return Err(ShaderContractDecline::Malformed { word: at });
        }
        let operands = &words[at + 1..at + count];
        let min_operands = match opcode {
            15 => 3, // OpEntryPoint: model, function, name
            17 => 1, // OpCapability
            25 => 8, // OpTypeImage: sampled=2 identifies storage images
            28 => 3, // OpTypeArray
            29 => 2, // OpTypeRuntimeArray
            30 => 1, // OpTypeStruct
            32 => 3, // OpTypePointer
            59 => 3, // OpVariable: type, result, storage
            71 => 2, // OpDecorate
            72 => 3, // OpMemberDecorate
            _ => 0,
        };
        if operands.len() < min_operands {
            return Err(ShaderContractDecline::Malformed { word: at });
        }
        match opcode {
            15 => {
                stages.insert(operands[0]);
            }
            17 => {
                capabilities.insert(operands[0]);
            }
            25 if operands[6] == 2 => {
                storage_images.insert(operands[0]);
            }
            28 | 29 => {
                arrays.insert(operands[0], operands[1]);
            }
            30 => {
                struct_members.insert(operands[0], operands.len() - 1);
            }
            32 => {
                pointees.insert(operands[0], operands[2]);
            }
            59 => {
                variables.push((operands[0], operands[1], operands[2]));
            }
            71 if operands[1] == 24 => {
                nonwritable.insert(operands[0]);
            }
            71 if operands[1] == 3 => {
                buffer_blocks.insert(operands[0]);
            }
            72 if operands[2] == 24 => {
                nonwritable_members.insert((operands[0], operands[1]));
            }
            _ => {}
        }
        at += count;
    }
    if capabilities.contains(&4441) || capabilities.contains(&4442) {
        require(
            features.variable_pointers_storage_buffer,
            ShaderFeature::VariablePointersStorageBuffer,
        )?;
    }
    if capabilities.contains(&4442) {
        require(
            features.variable_pointers && features.variable_pointers_storage_buffer,
            ShaderFeature::VariablePointers,
        )?;
    }
    if capabilities.contains(&5379) {
        require(
            features.shader_demote_to_helper_invocation,
            ShaderFeature::DemoteToHelperInvocation,
        )?;
    }
    if capabilities.contains(&55) {
        // This engine does not enable shaderStorageImageReadWithoutFormat.
        require(false, ShaderFeature::StorageImageReadWithoutFormat)?;
    }
    if capabilities.contains(&56) {
        require(
            features.storage_image_write_without_format,
            ShaderFeature::StorageImageWriteWithoutFormat,
        )?;
    }
    if capabilities.contains(&49) {
        require(
            features.storage_image_extended_formats,
            ShaderFeature::StorageImageExtendedFormats,
        )?;
    }
    let writable_storage = variables.iter().any(|&(pointer, variable, storage)| {
        if nonwritable.contains(&variable) {
            return false;
        }
        let mut pointee = pointees.get(&pointer).copied().unwrap_or(0);
        // Descriptor arrays can wrap a storage buffer or image. Bound the walk
        // even for malformed cyclic input; validation remains a separate gate.
        for _ in 0..32 {
            let Some(next) = arrays.get(&pointee) else {
                break;
            };
            pointee = *next;
        }
        if let Some(&members) = struct_members.get(&pointee) {
            if members > 0
                && (0..members).all(|m| nonwritable_members.contains(&(pointee, m as u32)))
            {
                return false;
            }
        }
        storage == 12 // StorageBuffer
            || (storage == 2 && buffer_blocks.contains(&pointee)) // legacy Uniform/BufferBlock
            || (storage == 0 && storage_images.contains(&pointee)) // UniformConstant storage image
    });
    if writable_storage && stages.iter().any(|stage| *stage <= 3) {
        require(
            features.vertex_pipeline_stores_and_atomics,
            ShaderFeature::VertexPipelineStoresAndAtomics,
        )?;
    }
    if writable_storage && stages.contains(&4) {
        require(
            features.fragment_stores_and_atomics,
            ShaderFeature::FragmentStoresAndAtomics,
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn graphics_storage_optional_format_capabilities_are_enabled_or_declined() {
        let enabled = DeviceFeatures {
            storage_image_write_without_format: true,
            storage_image_extended_formats: true,
            ..Default::default()
        };
        for (cap, feature) in [
            (56, ShaderFeature::StorageImageWriteWithoutFormat),
            (49, ShaderFeature::StorageImageExtendedFormats),
        ] {
            let words = module(&[(17, &[cap])]);
            assert_eq!(
                check(&words, &DeviceFeatures::default()),
                Err(ShaderContractDecline::MissingFeature { feature })
            );
            assert_eq!(check(&words, &enabled), Ok(()));
        }
        assert_eq!(
            check(&module(&[(17, &[55])]), &enabled),
            Err(ShaderContractDecline::MissingFeature {
                feature: ShaderFeature::StorageImageReadWithoutFormat
            })
        );
    }

    fn module(instructions: &[(u32, &[u32])]) -> Vec<u32> {
        let mut words = vec![0x0723_0203, 0x0001_0400, 0, 100, 0];
        for (op, args) in instructions {
            words.push(((args.len() as u32 + 1) << 16) | op);
            words.extend_from_slice(args);
        }
        words
    }

    #[test]
    fn optional_capabilities_require_enabled_features() {
        for (cap, feature) in [
            (4441, ShaderFeature::VariablePointersStorageBuffer),
            (5379, ShaderFeature::DemoteToHelperInvocation),
        ] {
            let words = module(&[(17, &[cap])]);
            assert_eq!(
                check(&words, &DeviceFeatures::default()),
                Err(ShaderContractDecline::MissingFeature { feature })
            );
            let enabled = DeviceFeatures {
                variable_pointers_storage_buffer: true,
                shader_demote_to_helper_invocation: true,
                ..DeviceFeatures::default()
            };
            assert_eq!(check(&words, &enabled), Ok(()));
        }
        let words = module(&[(17, &[4442])]);
        let storage_only = DeviceFeatures {
            variable_pointers_storage_buffer: true,
            ..Default::default()
        };
        assert_eq!(
            check(&words, &storage_only),
            Err(ShaderContractDecline::MissingFeature {
                feature: ShaderFeature::VariablePointers
            })
        );
        assert_eq!(
            check(
                &words,
                &DeviceFeatures {
                    variable_pointers: true,
                    ..storage_only
                }
            ),
            Ok(())
        );
    }

    #[test]
    fn storage_writes_are_gated_per_shader_stage() {
        for (stage, feature) in [
            (0, ShaderFeature::VertexPipelineStoresAndAtomics),
            (4, ShaderFeature::FragmentStoresAndAtomics),
        ] {
            let words = module(&[(15, &[stage, 10, 0]), (32, &[2, 12, 1]), (59, &[2, 3, 12])]);
            assert_eq!(
                check(&words, &DeviceFeatures::default()),
                Err(ShaderContractDecline::MissingFeature { feature })
            );
            let enabled = DeviceFeatures {
                vertex_pipeline_stores_and_atomics: true,
                fragment_stores_and_atomics: true,
                ..Default::default()
            };
            assert_eq!(check(&words, &enabled), Ok(()));
        }
        let compute = module(&[(15, &[5, 10, 0]), (32, &[2, 12, 1]), (59, &[2, 3, 12])]);
        assert_eq!(check(&compute, &DeviceFeatures::default()), Ok(()));
    }

    #[test]
    fn readonly_variable_or_all_block_members_do_not_require_stage_writes() {
        for decorations in [
            vec![(71, vec![3, 24])],
            vec![(72, vec![1, 0, 24]), (72, vec![1, 1, 24])],
        ] {
            let mut words = module(&[
                (15, &[4, 10, 0]),
                (30, &[1, 8, 8]),
                (32, &[2, 12, 1]),
                (59, &[2, 3, 12]),
            ]);
            for (op, args) in decorations {
                words.push(((args.len() as u32 + 1) << 16) | op);
                words.extend(args);
            }
            assert_eq!(check(&words, &DeviceFeatures::default()), Ok(()));
        }
        let partial = module(&[
            (15, &[4, 10, 0]),
            (72, &[1, 0, 24]),
            (30, &[1, 8, 8]),
            (32, &[2, 12, 1]),
            (59, &[2, 3, 12]),
        ]);
        assert!(matches!(
            check(&partial, &DeviceFeatures::default()),
            Err(ShaderContractDecline::MissingFeature { .. })
        ));
    }

    #[test]
    fn storage_images_and_descriptor_arrays_require_stage_writes_but_sampled_images_do_not() {
        for sampled in [1, 2] {
            let words = module(&[
                (15, &[4, 10, 0]),
                (25, &[1, 8, 1, 0, 0, 0, sampled, 0]),
                (28, &[4, 1, 5]),
                (32, &[2, 0, 4]),
                (59, &[2, 3, 0]),
            ]);
            assert_eq!(
                check(&words, &DeviceFeatures::default()).is_ok(),
                sampled == 1
            );
        }
    }

    #[test]
    fn malformed_instruction_lengths_are_rejected_without_panicking() {
        for words in [
            vec![],
            vec![0; 5],
            module(&[(17, &[])]),
            module(&[(15, &[])]),
        ] {
            assert!(matches!(
                check(&words, &DeviceFeatures::default()),
                Err(ShaderContractDecline::Malformed { .. })
            ));
        }
        for length in [0, 2, 65535] {
            let mut words = module(&[]);
            words.push(length << 16 | 17);
            assert!(matches!(
                check(&words, &DeviceFeatures::default()),
                Err(ShaderContractDecline::Malformed { .. })
            ));
        }
    }
}
