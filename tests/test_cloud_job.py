import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import DatasetRegistry, run_cloud_job


REGISTRY_PATH = Path("data/dataset_registry.json")
SAMPLE_DIR = Path("examples/manifests")


class CloudJobTests(unittest.TestCase):
    def test_run_cloud_job_writes_collectable_project_and_pipeline_outputs(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"cloud-job-{uuid.uuid4().hex}"

        result = run_cloud_job(
            registry,
            output_dir,
            pet_mr_manifest=SAMPLE_DIR / "adni-case-selection.sample.json",
            wsi_manifest=SAMPLE_DIR / "tcga-wsi-preprocessing.sample.json",
            ct_manifest=SAMPLE_DIR / "lidc-ct-prototype.sample.json",
            pairing_manifest=SAMPLE_DIR / "ct-wsi-pairing-audit.sample.json",
        )

        self.assertTrue((output_dir / "job_summary.json").exists())
        self.assertTrue((output_dir / "project-dry-run" / "manifest.json").exists())
        self.assertTrue((output_dir / "pipeline-run" / "pipeline_report.json").exists())
        self.assertTrue((output_dir / "synthetic-runtime" / "demo_summary.json").exists())
        self.assertTrue(result.project_package_validation.passed)
        self.assertTrue(result.dry_run_only)
        self.assertFalse(result.data_downloaded)
        self.assertEqual(result.pipeline_run.report.branch_count, 4)
        self.assertEqual(result.synthetic_runtime.summary["pet_mr_fusion_records"], 3)

        summary = json.loads((output_dir / "job_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["cloud_runnable"])
        self.assertEqual(summary["schema_version"], "brainfusion-cloud-job/v1")
        self.assertEqual(summary["synthetic_runtime_summary"]["release_stage"], "synthetic-runtime-demo")
        self.assertEqual(summary["ready_pipeline_branches"], ["pet-mr-fusion", "wsi-preprocessing", "ct-preprocessing"])
        self.assertEqual(summary["blocked_pipeline_branches"][0]["branch_id"], "ct-wsi-pairing")
        self.assertFalse(summary["publishable_main_conclusion_supported"])
        self.assertFalse(summary["extension_experiment_supported"])

    def test_cloud_job_summary_keeps_no_download_boundary(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"cloud-job-boundary-{uuid.uuid4().hex}"

        run_cloud_job(registry, output_dir)

        summary_text = (output_dir / "job_summary.json").read_text(encoding="utf-8")
        self.assertIn('"data_downloaded": false', summary_text)
        self.assertIn('"downloads_blocked": true', summary_text)
        self.assertNotIn("local_path", summary_text)
        self.assertNotIn("download_path", summary_text)


if __name__ == "__main__":
    unittest.main()
