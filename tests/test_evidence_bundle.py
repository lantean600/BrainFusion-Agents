import unittest
from pathlib import Path

from brainfusion_agents import (
    DatasetRegistry,
    build_dry_run_evidence_bundle,
    validate_trace,
)


REGISTRY_PATH = Path("data/dataset_registry.json")


class EvidenceBundleTests(unittest.TestCase):
    def test_pet_mr_dry_run_bundle_creates_planned_artifacts_and_valid_traces(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        bundle = build_dry_run_evidence_bundle(registry, ["adni", "oasis-3"])

        self.assertEqual(bundle.workflow_id, "pet_mr_mainline")
        self.assertTrue(bundle.downloads_blocked)
        self.assertFalse(bundle.data_downloaded)
        self.assertIn("agent_trace_bundle", bundle.planned_artifacts)
        self.assertEqual(bundle.artifact_status["agent_trace_bundle"], "planned")
        self.assertIn("Dataset downloads are blocked", " ".join(bundle.limitations))
        self.assertGreaterEqual(len(bundle.traces), 1)
        for trace in bundle.traces:
            self.assertEqual(validate_trace(trace), ())
            self.assertFalse(trace.conclusion_support.supports_main_conclusion)
            self.assertFalse(trace.conclusion_support.supports_extension_experiment)

    def test_unpaired_ct_wsi_dry_run_keeps_pairing_audit_and_blocks_fusion(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        bundle = build_dry_run_evidence_bundle(registry, ["lidc-idri", "tcga-gdc-wsi"])

        self.assertEqual(bundle.workflow_id, "ct_wsi_separate_with_pairing_audit")
        self.assertIn("pairing_audit_report", bundle.planned_artifacts)
        self.assertNotIn("ct_wsi_fusion_report", bundle.planned_artifacts)
        categories = {trace.failure.category for trace in bundle.traces}
        self.assertIn("pairing-unverified", categories)


if __name__ == "__main__":
    unittest.main()

