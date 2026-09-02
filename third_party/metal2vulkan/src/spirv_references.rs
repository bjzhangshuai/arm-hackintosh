//! Grammar-derived operand references for consumers of serialized SPIR-V.
//! Numeric literals, enum values, strings and result definitions are not uses.

use crate::spirv_module::Operand;

/// ID operands of one instruction, in serialized instruction order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InstructionReferences {
    pub opcode: u16,
    pub ids: Vec<u32>,
}

/// Decode ID operands with the same locked grammar as the translator.
///
/// Result IDs and result types are excluded. This is operand decoding, not
/// semantic validation or a control-flow/liveness analysis. Unknown opcodes
/// and malformed operands return an error rather than treating literals as IDs.
pub fn spirv_instruction_references(words: &[u32]) -> Result<Vec<InstructionReferences>, String> {
    let bytes = words
        .iter()
        .flat_map(|w| w.to_le_bytes())
        .collect::<Vec<_>>();
    let parsed = crate::spirv_binary::parse_bytes(&bytes).map_err(|e| e.to_string())?;
    Ok(parsed
        .instructions
        .into_iter()
        .map(|instruction| InstructionReferences {
            opcode: instruction.class.opcode as u16,
            ids: instruction
                .operands
                .into_iter()
                .filter_map(|operand| match operand {
                    Operand::IdRef(id) | Operand::IdScope(id) | Operand::IdMemorySemantics(id) => {
                        Some(id)
                    }
                    _ => None,
                })
                .collect(),
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn grammar_separates_literal_collisions_from_real_id_operands() {
        let mut words = vec![0x0723_0203, 0x10000, 0, 128, 0];
        for (opcode, operands) in [
            (22, vec![1, 32]),             // float width, not ID 32
            (21, vec![2, 32, 0]),          // integer width
            (43, vec![2, 3, 32]),          // constant literal
            (71, vec![4, 33, 32]),         // descriptor binding literal
            (79, vec![5, 6, 7, 8, 32, 0]), // shuffle component literals
            (12, vec![1, 9, 10, 32, 11]),  // extended opcode literal
            (99, vec![32, 12, 13]),        // a real image ID
        ] {
            words.push(((operands.len() as u32 + 1) << 16) | opcode);
            words.extend(operands);
        }
        let uses = spirv_instruction_references(&words).unwrap();
        assert_eq!(
            uses.iter().map(|i| i.ids.as_slice()).collect::<Vec<_>>(),
            [
                vec![],
                vec![],
                vec![],
                vec![4],
                vec![7, 8],
                vec![10, 11],
                vec![32, 12, 13]
            ]
            .iter()
            .map(Vec::as_slice)
            .collect::<Vec<_>>()
        );
    }

    #[test]
    fn malformed_or_unknown_instructions_never_report_empty_use_sets() {
        for instruction in [vec![0], vec![(2 << 16) | 65535, 1], vec![(4 << 16) | 99, 1]] {
            let mut words = vec![0x0723_0203, 0x10000, 0, 128, 0];
            words.extend(instruction);
            assert!(spirv_instruction_references(&words).is_err());
        }
        assert!(spirv_instruction_references(&[]).is_err());
    }
}
