import unittest

from brainfusion_agents import WorkflowRequest, route_workflow


class WorkflowRoutingTests(unittest.TestCase):
    def test_pet_mr_routes_to_mainline(self) -> None:
        route = route_workflow(WorkflowRequest.from_modalities(["PET", "MR"]))

        self.assertEqual(route.route, "pet_mr_mainline")
        self.assertEqual(route.claim_level, "main-conclusion-eligible")
        self.assertIn("PET/MR Fusion Agent", route.required_agents)

    def test_unpaired_ct_wsi_routes_to_pairing_audit_without_fusion_claim(self) -> None:
        route = route_workflow(WorkflowRequest.from_modalities(["CT", "WSI"]))

        self.assertEqual(route.route, "ct_wsi_separate_with_pairing_audit")
        self.assertEqual(route.claim_level, "no-fusion-claim")
        self.assertIn("Pairing Gate Agent", route.required_agents)


if __name__ == "__main__":
    unittest.main()

