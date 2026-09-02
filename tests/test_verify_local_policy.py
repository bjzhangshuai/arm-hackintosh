from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "macvm_verify_local_policy", ROOT / "tools" / "verify_local_policy.py"
)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


NONCE = "1b68377784ff5e40a73c78bae41d36f88ce56c2d98cc21a38b53935518ce5b63"
NSIH = "11" * 48
DGST = VERIFY.EMPTY_LOCAL_POLICY_SHA384.hex()


def summary(**changes: str) -> str:
    values = {
        "type": "lpol",
        "BNCH": NONCE,
        "BORD": "32",
        "CHIP": "65024",
        "ECID": "1234605616436508552",
        "CPRO": "true",
        "CSEC": "true",
        "lobo": "false",
        "nsih": NSIH,
        "DGST": DGST,
    }
    values.update(changes)
    return f"""IMG4:
IM4P: ---------
type: {values['type']}
desc: 1.0
   [BNCH]: BNCH: {values['BNCH']}
   [BORD]: BORD: {values['BORD']}
   [CHIP]: CHIP: {values['CHIP']}
   [CPRO]: CPRO: {values['CPRO']}
   [CSEC]: CSEC: {values['CSEC']}
   [ECID]: ECID: {values['ECID']}
   [nsih]: nsih: {values['nsih']}
   [lobo]: lobo: {values['lobo']}
      [DGST]: DGST: {values['DGST']}
"""


class LocalPolicyVerificationTests(unittest.TestCase):
    def verify(self, text: str, nonce: str = NONCE) -> dict[str, object]:
        return VERIFY.verify_local_policy_summary(
            text,
            expected_apnonce_hex=nonce,
            expected_board=32,
            expected_chip=0xFE00,
            expected_ecid=0x1122334455667788,
            expected_next_stage_im4m_sha384=bytes.fromhex(NSIH),
        )

    def test_accepts_matching_secure_local_policy(self) -> None:
        result = self.verify(summary())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["payload_type"], "lpol")
        self.assertEqual(result["bnch_bytes"], 32)
        self.assertTrue(result["bnch_matches_expected"])
        self.assertTrue(result["next_stage_hash_matches_expected"])
        self.assertTrue(result["payload_digest_matches_expected"])

    def test_rejects_invalid_expected_nonce_width(self) -> None:
        for nonce in ("", "00" * 31, "00" * 33, "not-hex"):
            with self.subTest(nonce=nonce), self.assertRaisesRegex(
                VERIFY.LocalPolicyVerificationError, "exactly 32 bytes"
            ):
                self.verify(summary(), nonce)

    def test_rejects_bnch_mismatch_and_wrong_width(self) -> None:
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "does not match"
        ):
            self.verify(summary(BNCH="00" * 32))
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "exactly 32 bytes"
        ):
            self.verify(summary(BNCH="00" * 48))

    def test_rejects_wrong_payload_or_identity(self) -> None:
        for field, value, message in (
            ("type", "ibss", "payload type"),
            ("BORD", "33", "BORD mismatch"),
            ("CHIP", "1", "CHIP mismatch"),
            ("ECID", "1", "ECID mismatch"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                VERIFY.LocalPolicyVerificationError, message
            ):
                self.verify(summary(**{field: value}))

    def test_rejects_insecure_policy_flags(self) -> None:
        for field, value in (("CPRO", "false"), ("CSEC", "false"), ("lobo", "true")):
            with self.subTest(field=field), self.assertRaisesRegex(
                VERIFY.LocalPolicyVerificationError, "CPRO=true"
            ):
                self.verify(summary(**{field: value}))

    def test_rejects_missing_or_duplicate_fields(self) -> None:
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "exactly one BNCH, found 0"
        ):
            self.verify(summary().replace(f"   [BNCH]: BNCH: {NONCE}\n", ""))
        duplicate = summary() + f"   [BNCH]: BNCH: {NONCE}\n"
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "exactly one BNCH, found 2"
        ):
            self.verify(duplicate)

    def test_rejects_malformed_manifest_digests(self) -> None:
        for field in ("nsih", "DGST"):
            with self.subTest(field=field), self.assertRaisesRegex(
                VERIFY.LocalPolicyVerificationError, "exactly 48 bytes"
            ):
                self.verify(summary(**{field: "00" * 47}))

    def test_rejects_wrong_manifest_digests(self) -> None:
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "nsih does not match"
        ):
            self.verify(summary(nsih="00" * 48))
        with self.assertRaisesRegex(
            VERIFY.LocalPolicyVerificationError, "DGST does not match"
        ):
            self.verify(summary(DGST="00" * 48))


if __name__ == "__main__":
    unittest.main()
