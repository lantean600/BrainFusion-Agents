import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import DatasetRegistry, materialize_pipeline_run


REGISTRY_PATH = Path("data/dataset_registry.json")
SAMPLE_DIR = Path("examples/manifests")


class PipelineTests(unittest.TestCase):
    def test_materialize_pipeline_run_writes_preprocessing_and_fusion_artifacts(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"pipeline-{uuid.uuid4().hex}"

        run = materialize_pipeline_run(
            registry,
            output_dir,
            pet_mr_manifest=SAMPLE_DIR / "adni-case-selection.sample.json",
            wsi_manifest=SAMPLE_DIR / "tcga-wsi-preprocessing.sample.json",
            ct_manifest=SAMPLE_DIR / "lidc-ct-prototype.sample.json",
            pairing_manifest=SAMPLE_DIR / "ct-wsi-pairing-audit.sample.json",
        )

        self.assertTrue((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "pipeline_report.json").exists())
        self.assertEqual(run.report.branch_count, 4)
        self.assertFalse(run.report.data_downloaded)

        by_branch = {branch.branch_id: branch for branch in run.report.branches}
        self.assertEqual(by_branch["pet-mr-fusion"].status, "ready")
        self.assertEqual(by_branch["wsi-preprocessing"].status, "ready")
        self.assertEqual(by_branch["ct-preprocessing"].status, "ready")
        self.assertEqual(by_branch["ct-wsi-pairing"].status, "blocked")
        self.assertIn("pet_mr_fusion_plan", by_branch["pet-mr-fusion"].artifacts)
        self.assertIn("patch_extraction_plan", by_branch["wsi-preprocessing"].artifacts)
        self.assertIn("ct_feature_extraction_plan", by_branch["ct-preprocessing"].artifacts)
        self.assertIn("ct_wsi_fusion_blocker_report", by_branch["ct-wsi-pairing"].artifacts)

    def test_pipeline_artifact_files_remain_dry_run_only(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"pipeline-dry-run-{uuid.uuid4().hex}"

        run = materialize_pipeline_run(
            registry,
            output_dir,
            pet_mr_manifest=SAMPLE_DIR / "adni-case-selection.sample.json",
        )

        forbidden = ("local_path", "download_path", '"data_downloaded": true')
        for path in run.files:
            if path.suffix != ".json":
                continue
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text)

    def test_pipeline_report_json_is_collectable(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"pipeline-report-{uuid.uuid4().hex}"

        materialize_pipeline_run(
            registry,
            output_dir,
            pet_mr_manifest=SAMPLE_DIR / "adni-case-selection.sample.json",
        )
        report = json.loads((output_dir / "pipeline_report.json").read_text(encoding="utf-8"))

        self.assertEqual(report["release_stage"], "pipeline-dry-run")
        self.assertTrue(report["dry_run_only"])
        self.assertFalse(report["data_downloaded"])
        self.assertEqual(report["branch_count"], 4)


if __name__ == "__main__":
    unittest.main()
