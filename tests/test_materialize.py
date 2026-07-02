import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import (
    DatasetRegistry,
    build_dry_run_evidence_bundle,
    materialize_dry_run_evidence_bundle,
)


REGISTRY_PATH = Path("data/dataset_registry.json")
TEST_TMP_ROOT = Path("test-output")


class MaterializeTests(unittest.TestCase):
    def test_materializes_dry_run_evidence_package(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        bundle = build_dry_run_evidence_bundle(registry, ["adni", "oasis-3"])

        root = _test_output_dir()
        package = materialize_dry_run_evidence_bundle(bundle, root)

        self.assertEqual(package.package_root, root)
        self.assertTrue((root / "manifest.json").exists())
        self.assertTrue((root / "evidence_bundle.json").exists())
        self.assertTrue((root / "traces").is_dir())
        self.assertTrue((root / "artifacts").is_dir())
        self.assertGreaterEqual(len(list((root / "traces").glob("*.json"))), 1)
        self.assertIn(root / "artifacts" / "agent_trace_bundle.json", package.files)

        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["workflow_id"], "pet_mr_mainline")
        self.assertTrue(manifest["downloads_blocked"])
        self.assertFalse(manifest["data_downloaded"])

        artifact = json.loads(
            (root / "artifacts" / "agent_trace_bundle.json").read_text(encoding="utf-8")
        )
        self.assertEqual(artifact["status"], "planned")
        self.assertFalse(artifact["data_downloaded"])

    def test_unpaired_ct_wsi_materialization_has_no_fusion_artifact(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        bundle = build_dry_run_evidence_bundle(registry, ["lidc-idri", "tcga-gdc-wsi"])

        root = _test_output_dir()
        materialize_dry_run_evidence_bundle(bundle, root)

        self.assertTrue((root / "artifacts" / "pairing_audit_report.json").exists())
        self.assertFalse((root / "artifacts" / "ct_wsi_fusion_report.json").exists())


def _test_output_dir() -> Path:
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    return TEST_TMP_ROOT / f"materialize-{uuid.uuid4().hex}"


if __name__ == "__main__":
    unittest.main()
