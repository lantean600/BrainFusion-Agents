import unittest
from pathlib import Path

from brainfusion_agents import DatasetRegistry, build_project_status_report


REGISTRY_PATH = Path("data/dataset_registry.json")


def pet_mr_manifest() -> dict:
    return {
        "manifest_type": "pet_mr_case_selection",
        "dataset_id": "adni",
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


def wsi_manifest() -> dict:
    return {
        "manifest_type": "wsi_preprocessing",
        "dataset_id": "tcga-gdc-wsi",
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


def ct_manifest() -> dict:
    return {
        "manifest_type": "ct_prototype",
        "dataset_id": "lidc-idri",
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


def unverified_pairing_manifest() -> dict:
    return {
        "manifest_type": "ct_pathology_pairing_audit",
        "source_datasets": ["tcia", "tcga-gdc"],
        "identifier_fields": ["submitter_id"],
        "paired_patient_count": 0,
        "paired_lesion_count": None,
        "timing_assumption": "",
        "endpoint_available": False,
        "evidence": [],
    }


class ProjectStatusTests(unittest.TestCase):
    def test_project_status_without_manifests_is_cloud_runnable_dry_run(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_project_status_report(registry)

        self.assertTrue(report.cloud_runnable)
        self.assertTrue(report.dry_run_only)
        self.assertFalse(report.data_downloaded)
        self.assertTrue(report.no_download_enforced)
        self.assertTrue(report.registry_passed)
        self.assertFalse(report.pet_mr_mvp_metadata_ready)
        self.assertFalse(report.publishable_main_conclusion_supported)
        self.assertEqual(len(report.branches), 4)
        self.assertTrue(all(not branch.manifest_provided for branch in report.branches))
        self.assertIn(
            "pet-mr-mvp: PET/MR case selection manifest was not provided.",
            report.metadata_blockers,
        )

    def test_project_status_marks_ready_branch_manifests_and_blocks_pairing(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)

        report = build_project_status_report(
            registry,
            pet_mr_manifest=pet_mr_manifest(),
            wsi_manifest=wsi_manifest(),
            ct_manifest=ct_manifest(),
            pairing_manifest=unverified_pairing_manifest(),
        )

        by_branch = {branch.branch_id: branch for branch in report.branches}

        self.assertTrue(report.cloud_runnable)
        self.assertTrue(report.pet_mr_mvp_metadata_ready)
        self.assertFalse(report.publishable_main_conclusion_supported)
        self.assertTrue(by_branch["wsi-preprocessing"].metadata_ready)
        self.assertTrue(by_branch["ct-prototype"].metadata_ready)
        self.assertFalse(by_branch["ct-pathology-pairing"].metadata_ready)
        self.assertEqual(
            by_branch["ct-pathology-pairing"].workflow_id,
            "ct_wsi_separate_with_pairing_audit",
        )
        self.assertIn(
            "ct-pathology-pairing: CT-pathology pairing gate did not pass.",
            report.metadata_blockers,
        )

    def test_project_status_allows_pairing_route_only_after_gate_passes(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        pairing = unverified_pairing_manifest()
        pairing["paired_patient_count"] = 12
        pairing["timing_assumption"] = "CT and WSI are linked to the same diagnostic episode."
        pairing["endpoint_available"] = True

        report = build_project_status_report(registry, pairing_manifest=pairing)

        pairing_branch = {
            branch.branch_id: branch for branch in report.branches
        }["ct-pathology-pairing"]

        self.assertTrue(pairing_branch.metadata_ready)
        self.assertEqual(pairing_branch.workflow_id, "ct_pathology_fusion")
        self.assertEqual(pairing_branch.details["gate_status"], "pass")
        self.assertEqual(pairing_branch.details["pairing_level"], "patient-level")
        self.assertFalse(pairing_branch.claim_supported)


if __name__ == "__main__":
    unittest.main()
