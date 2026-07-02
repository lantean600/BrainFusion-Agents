import unittest
from pathlib import Path

from brainfusion_agents import DatasetRegistry, build_workflow_plan


REGISTRY_PATH = Path("data/dataset_registry.json")


class WorkflowPlanTests(unittest.TestCase):
    def test_pet_mr_plan_uses_adni_and_oasis_without_downloads(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        plan = build_workflow_plan(registry, ["adni", "oasis-3"])

        self.assertEqual(plan.route.route, "pet_mr_mainline")
        self.assertEqual(plan.dataset_ids, ("adni", "oasis-3"))
        self.assertTrue(plan.downloads_blocked)
        self.assertIn("pet_presence", plan.qc_gates)
        self.assertIn("mr_presence", plan.qc_gates)
        self.assertIn("agent_trace_bundle", plan.expected_artifacts)
        self.assertIn("ADNI", " ".join(plan.dataset_names))
        self.assertIn("OASIS-3", " ".join(plan.dataset_names))

    def test_wsi_plan_contains_preprocessing_gates(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        plan = build_workflow_plan(registry, ["tcga-gdc-wsi", "camelyon"])

        self.assertEqual(plan.route.route, "wsi_preprocessing")
        self.assertIn("tissue_detection", plan.qc_gates)
        self.assertIn("patch_manifest", plan.expected_artifacts)
        self.assertIn("wsi_embedding_manifest", plan.expected_artifacts)

    def test_ct_plan_contains_prototype_gates(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        plan = build_workflow_plan(registry, ["lidc-idri", "nsclc-radiomics"])

        self.assertEqual(plan.route.route, "ct_branch")
        self.assertIn("ct_series_readable", plan.qc_gates)
        self.assertIn("ct_feature_manifest", plan.expected_artifacts)

    def test_unpaired_ct_wsi_plan_blocks_fusion_artifacts(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        plan = build_workflow_plan(registry, ["lidc-idri", "tcga-gdc-wsi"])

        self.assertEqual(plan.route.route, "ct_wsi_separate_with_pairing_audit")
        self.assertEqual(plan.route.claim_level, "no-fusion-claim")
        self.assertIn("pairing_audit_report", plan.expected_artifacts)
        self.assertNotIn("ct_wsi_fusion_report", plan.expected_artifacts)

    def test_paired_ct_wsi_plan_allows_fusion_artifacts(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        plan = build_workflow_plan(
            registry,
            ["lidc-idri", "tcga-gdc-wsi"],
            pairing_verified=True,
            pairing_level="patient-level",
        )

        self.assertEqual(plan.route.route, "ct_pathology_fusion")
        self.assertIn("ct_wsi_fusion_report", plan.expected_artifacts)
        self.assertIn("pairing_gate_passed", plan.qc_gates)


if __name__ == "__main__":
    unittest.main()

