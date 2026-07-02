import json
import unittest
from pathlib import Path

from brainfusion_agents import (
    pairing_manifest_template,
    validate_pairing_manifest,
)


class PairingManifestTests(unittest.TestCase):
    def test_pairing_template_contains_no_local_paths(self) -> None:
        template = pairing_manifest_template()

        self.assertEqual(template["manifest_type"], "ct_pathology_pairing_audit")
        self.assertIn("evidence", template)
        self.assertNotIn("local_path", json.dumps(template))
        self.assertNotIn("download_path", json.dumps(template))

    def test_patient_level_pairing_manifest_passes(self) -> None:
        manifest = {
            "manifest_type": "ct_pathology_pairing_audit",
            "source_datasets": ["tcia", "tcga-gdc"],
            "identifier_fields": ["case_id"],
            "paired_patient_count": 12,
            "paired_lesion_count": None,
            "timing_assumption": "CT before diagnostic resection within recorded study window",
            "endpoint_available": True,
            "evidence": [
                {
                    "evidence_id": "audit-row-1",
                    "source_record": "pairing-audit:tcia:tcga-gdc",
                    "description": "Case IDs matched after de-identification review.",
                }
            ],
        }

        result = validate_pairing_manifest(manifest)

        self.assertTrue(result.passed)
        self.assertEqual(result.gate_status, "pass")
        self.assertEqual(result.pairing_level, "patient-level")

    def test_missing_identifiers_fails_pairing_manifest(self) -> None:
        manifest = {
            "manifest_type": "ct_pathology_pairing_audit",
            "source_datasets": ["tcia", "tcga-gdc"],
            "identifier_fields": [],
            "paired_patient_count": 0,
            "paired_lesion_count": None,
            "timing_assumption": "",
            "endpoint_available": False,
            "evidence": [],
        }

        result = validate_pairing_manifest(manifest)

        self.assertFalse(result.passed)
        messages = " ".join(finding.message for finding in result.errors)
        self.assertIn("identifier_fields", messages)
        self.assertIn("No patient-level paired records", messages)

    def test_pairing_manifest_forbids_local_paths(self) -> None:
        manifest = {
            "manifest_type": "ct_pathology_pairing_audit",
            "source_datasets": ["tcia", "tcga-gdc"],
            "identifier_fields": ["case_id"],
            "paired_patient_count": 1,
            "paired_lesion_count": None,
            "timing_assumption": "same episode",
            "endpoint_available": True,
            "local_path": "D:/data/pairing.csv",
            "evidence": [],
        }

        result = validate_pairing_manifest(manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("local_path" in finding.message for finding in result.errors))

    def test_pairing_manifest_file_validation_loads_json(self) -> None:
        path = Path("test-output") / "pairing-manifest-validation.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "manifest_type": "ct_pathology_pairing_audit",
                    "source_datasets": ["tcia", "tcga-gdc"],
                    "identifier_fields": [],
                    "paired_patient_count": 0,
                    "paired_lesion_count": None,
                    "timing_assumption": "",
                    "endpoint_available": False,
                    "evidence": [],
                }
            ),
            encoding="utf-8",
        )

        result = validate_pairing_manifest(path)

        self.assertFalse(result.passed)
        self.assertEqual(result.gate_status, "fail")


if __name__ == "__main__":
    unittest.main()

