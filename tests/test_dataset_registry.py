import unittest
from pathlib import Path

from brainfusion_agents import DatasetRegistry


REGISTRY_PATH = Path("data/dataset_registry.json")


class DatasetRegistryTests(unittest.TestCase):
    def test_registry_keeps_links_without_local_download_paths(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        records = registry.list()
        self.assertGreaterEqual(len(records), 10)
        for record in records:
            self.assertTrue(record.source_urls)
            self.assertNotEqual(record.access_status, "downloaded")

    def test_pet_mr_mainline_datasets_are_queryable(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        pet_records = {record.dataset_id for record in registry.by_modality("PET")}

        self.assertIn("adni", pet_records)
        self.assertIn("oasis-3", pet_records)
        self.assertEqual(registry.get("adni").role, "primary-development")
        self.assertEqual(registry.get("oasis-3").role, "external-validation")

    def test_bundled_registry_matches_workspace_registry_ids(self) -> None:
        workspace = DatasetRegistry.load(REGISTRY_PATH)
        bundled = DatasetRegistry.load_bundled()

        self.assertEqual(
            [record.dataset_id for record in workspace.list()],
            [record.dataset_id for record in bundled.list()],
        )


if __name__ == "__main__":
    unittest.main()
