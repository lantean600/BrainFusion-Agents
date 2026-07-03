import hashlib
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
            download_policy="off",
        )

        self.assertTrue((output_dir / "job_summary.json").exists())
        self.assertTrue((output_dir / "project-dry-run" / "manifest.json").exists())
        self.assertTrue((output_dir / "pipeline-run" / "pipeline_report.json").exists())
        self.assertTrue((output_dir / "synthetic-runtime" / "demo_summary.json").exists())
        self.assertTrue(result.project_package_validation.passed)
        self.assertTrue(result.dry_run_only)
        self.assertFalse(result.data_downloaded)
        self.assertIsNone(result.download_run)
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

        run_cloud_job(registry, output_dir, download_policy="off")

        summary_text = (output_dir / "job_summary.json").read_text(encoding="utf-8")
        self.assertIn('"data_downloaded": false', summary_text)
        self.assertIn('"downloads_blocked": true', summary_text)
        self.assertNotIn("local_path", summary_text)
        self.assertNotIn("download_path", summary_text)

    def test_cloud_job_can_execute_download_stage_with_custom_plan(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        source_dir = Path("test-output") / f"cloud-job-download-source-{uuid.uuid4().hex}"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "sample.npz"
        payload = b"cloud-job-download-stage"
        source_path.write_bytes(payload)
        checksum = hashlib.md5(payload).hexdigest()
        plan_path = source_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "datasets": [
                        {
                            "dataset_id": "local-cloud-job-tumor",
                            "name": "Local Cloud Job Tumor",
                            "modality_group": "CT",
                            "tumor_context": "cloud-job unit-test tumor download",
                            "download_method": "direct-http",
                            "url": source_path.resolve().as_uri(),
                            "filename": "sample.npz",
                            "md5": checksum,
                            "estimated_size_mb": 1,
                            "default_auto_download": True,
                            "license": "test",
                            "source": "test",
                            "notes": "Local file URL test.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        output_dir = Path("test-output") / f"cloud-job-download-{uuid.uuid4().hex}"

        result = run_cloud_job(
            registry,
            output_dir,
            download_policy="auto",
            download_plan=plan_path,
        )
        summary = json.loads((output_dir / "job_summary.json").read_text(encoding="utf-8"))

        self.assertTrue(result.data_downloaded)
        self.assertFalse(result.dry_run_only)
        self.assertEqual(result.download_run.download_count, 1)
        self.assertEqual(summary["release_stage"], "cloud-job-download")
        self.assertTrue((output_dir / "downloads" / "files" / "local-cloud-job-tumor" / "sample.npz").exists())


if __name__ == "__main__":
    unittest.main()
