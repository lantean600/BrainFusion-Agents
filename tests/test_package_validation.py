import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import DatasetRegistry, materialize_project_dry_run, validate_project_package


REGISTRY_PATH = Path("data/dataset_registry.json")


class PackageValidationTests(unittest.TestCase):
    def test_valid_project_dry_run_package_passes_validation(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"package-validation-{uuid.uuid4().hex}"
        materialize_project_dry_run(registry, output_dir)

        result = validate_project_package(output_dir)

        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.branch_count, 4)
        self.assertGreater(result.checked_file_count, 10)

    def test_validator_rejects_downloaded_evidence(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"package-validation-downloaded-{uuid.uuid4().hex}"
        materialize_project_dry_run(registry, output_dir)
        bundle_path = (
            output_dir
            / "branches"
            / "pet-mr-mvp"
            / "evidence"
            / "evidence_bundle.json"
        )
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload["data_downloaded"] = True
        bundle_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        result = validate_project_package(output_dir)

        self.assertFalse(result.passed)
        self.assertTrue(
            any("data_downloaded" in finding.message for finding in result.errors)
        )


if __name__ == "__main__":
    unittest.main()
