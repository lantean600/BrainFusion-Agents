import json
import unittest
from pathlib import Path

from brainfusion_agents import (
    DatasetRegistry,
    build_ct_readiness_report,
    build_pet_mr_readiness_report,
    build_wsi_readiness_report,
)


REGISTRY_PATH = Path("data/dataset_registry.json")


def valid_manifest(dataset_id: str = "adni") -> dict:
    return {
        "manifest_type": "pet_mr_case_selection",
        "dataset_id": dataset_id,
        "records": [
            {
                "subject_id": "S001",
                "session_id": "M00",
                "diagnosis_label": "MCI",
                "clinical_timepoint": "baseline",
                "pet_available": True,
                "mr_available": True,
                "pet_tracer": "FDG",
                "mr_sequence": "T1w",
                "pet_qc_status": "pass",
                "mr_qc_status": "pass",
                "alignment_status": "subject-session",
                "source_record": "adni:S001:M00",
            }
        ],
    }


def valid_wsi_manifest(dataset_id: str = "tcga-gdc-wsi") -> dict:
    return {
        "manifest_type": "wsi_preprocessing",
        "dataset_id": dataset_id,
        "records": [
            {
                "case_id": "CASE-001",
                "slide_id": "SLIDE-001",
                "source_record": "tcga:CASE-001:SLIDE-001",
                "magnification": "20x",
                "resolution": "0.5 mpp",
                "slide_readable": True,
                "tissue_detection_status": "pass",
                "artifact_filtering_status": "pass",
                "stain_normalization_status": "planned",
                "patch_extraction_status": "planned",
                "embedding_status": "planned",
                "patch_count": 0,
                "embedding_model": "UNI-candidate",
                "qc_status": "needs-human-review",
                "trace_id": "dry-run:wsi:SLIDE-001",
            }
        ],
    }


def valid_ct_manifest(dataset_id: str = "lidc-idri") -> dict:
    return {
        "manifest_type": "ct_prototype",
        "dataset_id": dataset_id,
        "records": [
            {
                "case_id": "LIDC-001",
                "study_id": "STUDY-001",
                "series_id": "SERIES-001",
                "source_record": "lidc:LIDC-001:STUDY-001:SERIES-001",
                "ct_protocol": "chest-ct",
                "ct_series_readable": True,
                "metadata_sufficient": True,
                "annotation_available": True,
                "lesion_reference": "nodule-1",
                "baseline_type": "segmentation",
                "baseline_status": "planned",
                "feature_manifest_status": "planned",
                "qc_status": "needs-human-review",
                "trace_id": "dry-run:ct:LIDC-001",
            }
        ],
    }


class ReadinessTests(unittest.TestCase):
    def test_valid_pet_mr_manifest_is_metadata_ready_but_not_claim_supporting(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_pet_mr_readiness_report(
            registry,
            ["adni", "oasis-3"],
            valid_manifest(),
        )

        self.assertTrue(report.metadata_ready)
        self.assertTrue(report.dry_run_only)
        self.assertFalse(report.can_support_main_conclusion)
        self.assertEqual(report.workflow_id, "pet_mr_mainline")
        self.assertEqual(report.manifest_record_count, 1)
        self.assertIn("pet_mr_fusion_report", report.planned_artifacts)

    def test_empty_manifest_blocks_metadata_readiness(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_pet_mr_readiness_report(
            registry,
            ["adni", "oasis-3"],
            {
                "manifest_type": "pet_mr_case_selection",
                "dataset_id": "adni",
                "records": [],
            },
        )

        self.assertFalse(report.metadata_ready)
        self.assertIn("Case selection manifest has no records.", report.blocking_reasons)

    def test_invalid_manifest_blocks_metadata_readiness(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        manifest = valid_manifest()
        manifest["records"][0]["mr_available"] = False

        report = build_pet_mr_readiness_report(registry, ["adni", "oasis-3"], manifest)

        self.assertFalse(report.metadata_ready)
        self.assertTrue(any("Manifest validation failed" in reason for reason in report.blocking_reasons))

    def test_manifest_dataset_must_be_in_selected_datasets(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_pet_mr_readiness_report(
            registry,
            ["adni", "oasis-3"],
            valid_manifest(dataset_id="openneuro"),
        )

        self.assertFalse(report.metadata_ready)
        self.assertIn("Manifest dataset_id openneuro is not in selected datasets.", report.blocking_reasons)

    def test_readiness_report_loads_manifest_file(self) -> None:
        path = Path("test-output") / "readiness-manifest.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(valid_manifest()), encoding="utf-8")
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_pet_mr_readiness_report(registry, ["adni", "oasis-3"], path)

        self.assertTrue(report.metadata_ready)

    def test_valid_wsi_manifest_is_extension_metadata_ready(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_wsi_readiness_report(
            registry,
            ["tcga-gdc-wsi", "camelyon"],
            valid_wsi_manifest(),
        )

        self.assertTrue(report.metadata_ready)
        self.assertTrue(report.dry_run_only)
        self.assertFalse(report.can_support_extension_experiment)
        self.assertEqual(report.workflow_id, "wsi_preprocessing")
        self.assertIn("wsi_embedding_manifest", report.planned_artifacts)

    def test_empty_wsi_manifest_blocks_metadata_readiness(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_wsi_readiness_report(
            registry,
            ["tcga-gdc-wsi"],
            {
                "manifest_type": "wsi_preprocessing",
                "dataset_id": "tcga-gdc-wsi",
                "records": [],
            },
        )

        self.assertFalse(report.metadata_ready)
        self.assertIn("WSI preprocessing manifest has no records.", report.blocking_reasons)

    def test_valid_ct_manifest_is_extension_metadata_ready(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_ct_readiness_report(
            registry,
            ["lidc-idri", "nsclc-radiomics"],
            valid_ct_manifest(),
        )

        self.assertTrue(report.metadata_ready)
        self.assertTrue(report.dry_run_only)
        self.assertFalse(report.can_support_extension_experiment)
        self.assertEqual(report.workflow_id, "ct_branch")
        self.assertIn("ct_feature_manifest", report.planned_artifacts)

    def test_invalid_ct_manifest_blocks_metadata_readiness(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        manifest = valid_ct_manifest()
        manifest["records"][0]["ct_series_readable"] = False

        report = build_ct_readiness_report(registry, ["lidc-idri"], manifest)

        self.assertFalse(report.metadata_ready)
        self.assertTrue(any("Manifest validation failed" in reason for reason in report.blocking_reasons))


if __name__ == "__main__":
    unittest.main()
