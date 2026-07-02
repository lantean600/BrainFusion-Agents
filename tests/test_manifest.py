import json
import unittest
from pathlib import Path

from brainfusion_agents import (
    case_selection_manifest_template,
    validate_case_selection_manifest,
)


class ManifestTests(unittest.TestCase):
    def test_case_selection_template_contains_no_local_paths(self) -> None:
        template = case_selection_manifest_template()

        self.assertEqual(template["manifest_type"], "pet_mr_case_selection")
        self.assertIn("records", template)
        self.assertEqual(template["records"], [])
        self.assertIn("required_record_fields", template)
        self.assertNotIn("local_path", json.dumps(template))
        self.assertNotIn("download_path", json.dumps(template))

    def test_valid_pet_mr_manifest_passes(self) -> None:
        manifest = {
            "manifest_type": "pet_mr_case_selection",
            "dataset_id": "adni",
            "records": [
                {
                    "subject_id": "S001",
                    "session_id": "M00",
                    "diagnosis_label": "MCI",
                    "clinical_timepoint": "baseline",
                    "pet_available": True,
                    "mr_available": True,
                    "pet_tracer": "FDG",
                    "mr_sequence": "T1w",
                    "pet_qc_status": "pass",
                    "mr_qc_status": "pass",
                    "alignment_status": "subject-session",
                    "source_record": "adni:S001:M00",
                }
            ],
        }

        result = validate_case_selection_manifest(manifest)

        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.record_count, 1)

    def test_missing_mr_or_label_fails(self) -> None:
        manifest = {
            "manifest_type": "pet_mr_case_selection",
            "dataset_id": "adni",
            "records": [
                {
                    "subject_id": "S001",
                    "session_id": "M00",
                    "diagnosis_label": "",
                    "clinical_timepoint": "baseline",
                    "pet_available": True,
                    "mr_available": False,
                    "pet_tracer": "FDG",
                    "mr_sequence": "",
                    "pet_qc_status": "pass",
                    "mr_qc_status": "fail",
                    "alignment_status": "missing-mr",
                    "source_record": "adni:S001:M00",
                }
            ],
        }

        result = validate_case_selection_manifest(manifest)

        self.assertFalse(result.passed)
        messages = " ".join(finding.message for finding in result.errors)
        self.assertIn("diagnosis_label", messages)
        self.assertIn("mr_available", messages)

    def test_manifest_with_local_paths_fails(self) -> None:
        manifest = {
            "manifest_type": "pet_mr_case_selection",
            "dataset_id": "adni",
            "records": [
                {
                    "subject_id": "S001",
                    "session_id": "M00",
                    "diagnosis_label": "CN",
                    "clinical_timepoint": "baseline",
                    "pet_available": True,
                    "mr_available": True,
                    "pet_tracer": "FDG",
                    "mr_sequence": "T1w",
                    "pet_qc_status": "pass",
                    "mr_qc_status": "pass",
                    "alignment_status": "subject-session",
                    "source_record": "adni:S001:M00",
                    "local_path": "D:/data/adni/S001",
                }
            ],
        }

        result = validate_case_selection_manifest(manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("local_path" in finding.message for finding in result.errors))

    def test_manifest_file_validation_loads_json(self) -> None:
        path = Path("test-output") / "manifest-validation.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "manifest_type": "pet_mr_case_selection",
                    "dataset_id": "oasis-3",
                    "records": [],
                }
            ),
            encoding="utf-8",
        )

        result = validate_case_selection_manifest(path)

        self.assertTrue(result.passed)
        self.assertEqual(result.record_count, 0)


if __name__ == "__main__":
    unittest.main()

