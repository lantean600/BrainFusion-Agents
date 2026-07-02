import json
import unittest
from pathlib import Path

from brainfusion_agents import ct_manifest_template, validate_ct_manifest


def valid_ct_manifest(dataset_id: str = "lidc-idri") -> dict:
    return {
        "manifest_type": "ct_prototype",
        "dataset_id": dataset_id,
        "records": [
            {
                "case_id": "LIDC-001",
                "study_id": "STUDY-001",
                "series_id": "SERIES-001",
                "source_record": "lidc:LIDC-001:STUDY-001:SERIES-001",
                "ct_protocol": "chest-ct",
                "ct_series_readable": True,
                "metadata_sufficient": True,
                "annotation_available": True,
                "lesion_reference": "nodule-1",
                "baseline_type": "segmentation",
                "baseline_status": "planned",
                "feature_manifest_status": "planned",
                "qc_status": "needs-human-review",
                "trace_id": "dry-run:ct:LIDC-001",
            }
        ],
    }


class CtManifestTests(unittest.TestCase):
    def test_ct_template_contains_no_local_paths(self) -> None:
        template = ct_manifest_template()

        self.assertEqual(template["manifest_type"], "ct_prototype")
        self.assertIn("required_record_fields", template)
        self.assertNotIn("dicom_path", json.dumps(template))
        self.assertNotIn("local_path", json.dumps(template))

    def test_valid_ct_manifest_passes(self) -> None:
        result = validate_ct_manifest(valid_ct_manifest())

        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.record_count, 1)

    def test_missing_series_or_baseline_fails(self) -> None:
        manifest = valid_ct_manifest()
        del manifest["records"][0]["series_id"]
        del manifest["records"][0]["baseline_type"]

        result = validate_ct_manifest(manifest)

        self.assertFalse(result.passed)
        messages = " ".join(finding.message for finding in result.errors)
        self.assertIn("series_id", messages)
        self.assertIn("baseline_type", messages)

    def test_ct_manifest_forbids_dicom_paths(self) -> None:
        manifest = valid_ct_manifest()
        manifest["records"][0]["dicom_path"] = "D:/ct/LIDC-001"

        result = validate_ct_manifest(manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("dicom_path" in finding.message for finding in result.errors))

    def test_ct_manifest_file_validation_loads_json(self) -> None:
        path = Path("test-output") / "ct-manifest-validation.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(valid_ct_manifest()), encoding="utf-8")

        result = validate_ct_manifest(path)

        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()

