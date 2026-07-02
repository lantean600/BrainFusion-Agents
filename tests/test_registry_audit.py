import unittest
from pathlib import Path

from brainfusion_agents import DatasetRecord, DatasetRegistry, audit_dataset_registry


REGISTRY_PATH = Path("data/dataset_registry.json")


class RegistryAuditTests(unittest.TestCase):
    def test_current_registry_passes_no_download_and_strategy_audit(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        result = audit_dataset_registry(registry)

        self.assertTrue(result.passed)
        self.assertEqual(result.error_count, 0)
        self.assertIn("adni", result.dataset_ids)
        self.assertIn("oasis-3", result.dataset_ids)

    def test_downloaded_access_status_is_an_error_in_current_phase(self) -> None:
        registry = DatasetRegistry(
            [
                DatasetRecord(
                    dataset_id="adni",
                    name="ADNI",
                    modalities=("PET", "MR"),
                    branch="pet-mr-mainline",
                    role="primary-development",
                    access_status="downloaded",
                    source_urls=("https://adni.loni.usc.edu/data-samples/adni-data/",),
                    pairing_status="subject-session-alignment-required",
                )
            ]
        )

        result = audit_dataset_registry(registry)

        self.assertFalse(result.passed)
        self.assertTrue(
            any("downloaded" in finding.message for finding in result.errors),
            result.errors,
        )

    def test_verified_ct_wsi_pairing_status_is_an_error_without_gate_evidence(self) -> None:
        registry = DatasetRegistry(
            [
                DatasetRecord(
                    dataset_id="paired",
                    name="Bad paired cohort",
                    modalities=("CT", "WSI"),
                    branch="ct-pathology-extension",
                    role="pairing-audit-candidate",
                    access_status="not-requested",
                    source_urls=("https://example.org",),
                    pairing_status="patient-level",
                )
            ]
        )

        result = audit_dataset_registry(registry)

        self.assertFalse(result.passed)
        self.assertTrue(
            any("must remain unverified" in finding.message for finding in result.errors),
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()

