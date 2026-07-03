import hashlib
import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import load_download_specs, materialize_tumor_downloads


class TumorDownloadTests(unittest.TestCase):
    def test_bundled_plan_defaults_to_tumor_auto_download_specs(self) -> None:
        specs = load_download_specs()
        default_ids = {spec.dataset_id for spec in specs if spec.default_auto_download}

        self.assertIn("medmnist-breastmnist", default_ids)
        self.assertIn("medmnist-nodulemnist3d", default_ids)
        self.assertIn("medmnist-pathmnist", default_ids)

    def test_plan_only_download_run_writes_manifest_without_data(self) -> None:
        output_dir = Path("test-output") / f"download-plan-{uuid.uuid4().hex}"

        result = materialize_tumor_downloads(
            output_dir,
            dataset_ids=("medmnist-breastmnist",),
            execute=False,
        )

        self.assertTrue((output_dir / "download_manifest.json").exists())
        self.assertTrue((output_dir / "download_summary.json").exists())
        self.assertFalse(result.data_downloaded)
        self.assertEqual(result.planned_count, 1)
        self.assertEqual(result.results[0].status, "planned")

    def test_execute_download_run_verifies_file_checksum(self) -> None:
        source_dir = Path("test-output") / f"download-source-{uuid.uuid4().hex}"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "sample.npz"
        payload = b"tumor-download-smoke"
        source_path.write_bytes(payload)
        checksum = hashlib.md5(payload).hexdigest()

        plan_path = source_dir / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "datasets": [
                        {
                            "dataset_id": "local-tumor-smoke",
                            "name": "Local Tumor Smoke",
                            "modality_group": "CT",
                            "tumor_context": "unit-test tumor download",
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
        output_dir = Path("test-output") / f"download-exec-{uuid.uuid4().hex}"

        result = materialize_tumor_downloads(
            output_dir,
            plan_path=plan_path,
            execute=True,
        )

        downloaded_path = output_dir / "files" / "local-tumor-smoke" / "sample.npz"
        self.assertTrue(downloaded_path.exists())
        self.assertTrue(result.data_downloaded)
        self.assertEqual(result.download_count, 1)
        self.assertEqual(result.results[0].md5, checksum)

    def test_download_size_budget_blocks_large_selection(self) -> None:
        output_dir = Path("test-output") / f"download-budget-{uuid.uuid4().hex}"

        with self.assertRaises(ValueError):
            materialize_tumor_downloads(
                output_dir,
                dataset_ids=("medmnist-pathmnist",),
                execute=False,
                max_download_mb=1,
            )


if __name__ == "__main__":
    unittest.main()
