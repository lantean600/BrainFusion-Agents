import unittest

from brainfusion_agents import PairingEvidence, evaluate_pairing_gate


class PairingGateTests(unittest.TestCase):
    def test_dataset_coavailability_without_patient_matches_fails(self) -> None:
        result = evaluate_pairing_gate(
            PairingEvidence(
                source_datasets=("tcia", "tcga-gdc"),
                identifier_fields=(),
                paired_patient_count=0,
                timing_assumption=None,
                endpoint_available=False,
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual(result.pairing_level, "none")
        self.assertIn("No patient-level paired records were verified.", result.limitations)

    def test_patient_level_evidence_passes_pairing_gate(self) -> None:
        result = evaluate_pairing_gate(
            PairingEvidence(
                source_datasets=("tcia", "tcga-gdc"),
                identifier_fields=("case_id",),
                paired_patient_count=42,
                timing_assumption="CT before diagnostic resection within recorded study window",
                endpoint_available=True,
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.pairing_level, "patient-level")
        self.assertEqual(result.paired_patient_count, 42)

    def test_lesion_level_evidence_takes_precedence(self) -> None:
        result = evaluate_pairing_gate(
            PairingEvidence(
                source_datasets=("nsclc-radiomics", "tcga-gdc-wsi"),
                identifier_fields=("case_id", "lesion_id"),
                paired_patient_count=12,
                paired_lesion_count=9,
                timing_assumption="Matched lesion documentation available",
                endpoint_available=True,
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.pairing_level, "lesion-level")
        self.assertEqual(result.paired_lesion_count, 9)


if __name__ == "__main__":
    unittest.main()

