import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import run_synthetic_runtime_demo


class SyntheticRuntimeTests(unittest.TestCase):
    def test_synthetic_runtime_writes_computed_medical_imaging_demo_outputs(self) -> None:
        output_dir = Path("test-output") / f"synthetic-runtime-{uuid.uuid4().hex}"

        result = run_synthetic_runtime_demo(output_dir, subject_count=2, seed=7)

        self.assertTrue((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "demo_summary.json").exists())
        self.assertTrue((output_dir / "pet_mr_fusion_demo.json").exists())
        self.assertTrue((output_dir / "ct_preprocessing_demo.json").exists())
        self.assertTrue((output_dir / "wsi_preprocessing_demo.json").exists())
        self.assertFalse(result.summary["data_downloaded"])
        self.assertTrue(result.summary["downloads_blocked"])
        self.assertEqual(result.summary["pet_mr_fusion_records"], 2)

        pet_mr = json.loads((output_dir / "pet_mr_fusion_demo.json").read_text(encoding="utf-8"))
        ct = json.loads((output_dir / "ct_preprocessing_demo.json").read_text(encoding="utf-8"))
        wsi = json.loads((output_dir / "wsi_preprocessing_demo.json").read_text(encoding="utf-8"))

        self.assertEqual(len(pet_mr["records"]), 2)
        self.assertGreater(pet_mr["records"][0]["voxel_count"], 0)
        self.assertEqual(ct["records"][0]["normalization"], "zscore")
        self.assertEqual(len(ct["records"][0]["feature_vector"]), 3)
        self.assertEqual(len(wsi["records"][0]["embedding"]), 8)

    def test_synthetic_runtime_rejects_empty_subject_count(self) -> None:
        output_dir = Path("test-output") / f"synthetic-runtime-empty-{uuid.uuid4().hex}"

        with self.assertRaises(ValueError):
            run_synthetic_runtime_demo(output_dir, subject_count=0)


if __name__ == "__main__":
    unittest.main()
