import json
import unittest
from pathlib import Path

from brainfusion_agents import (
    validate_wsi_manifest,
    wsi_manifest_template,
)


def valid_wsi_manifest(dataset_id: str = "tcga-gdc-wsi") -> dict:
    return {
        "manifest_type": "wsi_preprocessing",
        "dataset_id": dataset_id,
        "records": [
            {
                "case_id": "CASE-001",
                "slide_id": "SLIDE-001",
                "source_record": "tcga:CASE-001:SLIDE-001",
                "magnification": "20x",
                "resolution": "0.5 mpp",
                "slide_readable": True,
                "tissue_detection_status": "pass",
                "artifact_filtering_status": "pass",
                "stain_normalization_status": "planned",
                "patch_extraction_status": "planned",
                "embedding_status": "planned",
                "patch_count": 0,
                "embedding_model": "UNI-candidate",
                "qc_status": "needs-human-review",
                "trace_id": "dry-run:wsi:SLIDE-001",
            }
        ],
    }


class WsiManifestTests(unittest.TestCase):
    def test_wsi_template_contains_no_local_paths(self) -> None:
        template = wsi_manifest_template()

        self.assertEqual(template["manifest_type"], "wsi_preprocessing")
        self.assertIn("required_record_fields", template)
        self.assertNotIn("local_path", json.dumps(template))
        self.assertNotIn("slide_path", json.dumps(template))

    def test_valid_wsi_manifest_passes(self) -> None:
        result = validate_wsi_manifest(valid_wsi_manifest())

        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.record_count, 1)

    def test_missing_patch_and_embedding_status_fails(self) -> None:
        manifest = valid_wsi_manifest()
        del manifest["records"][0]["patch_extraction_status"]
        del manifest["records"][0]["embedding_status"]

        result = validate_wsi_manifest(manifest)

        self.assertFalse(result.passed)
        messages = " ".join(finding.message for finding in result.errors)
        self.assertIn("patch_extraction_status", messages)
        self.assertIn("embedding_status", messages)

    def test_wsi_manifest_forbids_local_slide_paths(self) -> None:
        manifest = valid_wsi_manifest()
        manifest["records"][0]["slide_path"] = "D:/slides/SLIDE-001.svs"

        result = validate_wsi_manifest(manifest)

        self.assertFalse(result.passed)
        self.assertTrue(any("slide_path" in finding.message for finding in result.errors))

    def test_wsi_manifest_file_validation_loads_json(self) -> None:
        path = Path("test-output") / "wsi-manifest-validation.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(valid_wsi_manifest()), encoding="utf-8")

        result = validate_wsi_manifest(path)

        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()

