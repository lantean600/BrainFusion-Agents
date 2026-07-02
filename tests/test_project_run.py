import json
import unittest
import uuid
from pathlib import Path

from brainfusion_agents import DatasetRegistry, materialize_project_dry_run


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


def pairing_manifest(paired_patient_count: int = 0) -> dict:
    return {
        "manifest_type": "ct_pathology_pairing_audit",
        "source_datasets": ["tcia", "tcga-gdc"],
        "identifier_fields": ["submitter_id"],
        "paired_patient_count": paired_patient_count,
        "paired_lesion_count": None,
        "timing_assumption": "same diagnostic episode" if paired_patient_count else "",
        "endpoint_available": bool(paired_patient_count),
        "evidence": [],
    }


class ProjectRunTests(unittest.TestCase):
    def test_materialize_project_dry_run_writes_branch_packages(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"project-dry-run-{uuid.uuid4().hex}"

        package = materialize_project_dry_run(
            registry,
            output_dir,
            pet_mr_manifest=pet_mr_manifest(),
            wsi_manifest=wsi_manifest(),
            ct_manifest=ct_manifest(),
            pairing_manifest=pairing_manifest(),
        )

        self.assertTrue((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "project_status.json").exists())
        self.assertEqual(len(package.branches), 4)
        self.assertTrue(package.status.cloud_runnable)
        self.assertFalse(package.status.data_downloaded)

        pairing_bundle = output_dir / "branches" / "ct-pathology-pairing" / "evidence" / "evidence_bundle.json"
        payload = json.loads(pairing_bundle.read_text(encoding="utf-8"))

        self.assertEqual(payload["workflow_id"], "ct_wsi_separate_with_pairing_audit")
        self.assertIn("pairing_audit_report", payload["planned_artifacts"])
        self.assertNotIn("ct_wsi_fusion_report", payload["planned_artifacts"])

    def test_materialized_project_package_has_no_local_data_paths(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"project-dry-run-paths-{uuid.uuid4().hex}"

        package = materialize_project_dry_run(registry, output_dir)

        forbidden = ("local_path", "download_path", "dicom_path", "slide_path", "patch_path")
        for path in package.files:
            if path.suffix != ".json":
                continue
            text = path.read_text(encoding="utf-8")
            for field in forbidden:
                self.assertNotIn(field, text)

    def test_materialize_project_dry_run_routes_verified_pairing_to_fusion_plan(self) -> None:
        registry = DatasetRegistry.load(REGISTRY_PATH)
        output_dir = Path("test-output") / f"project-dry-run-paired-{uuid.uuid4().hex}"

        package = materialize_project_dry_run(
            registry,
            output_dir,
            pairing_manifest=pairing_manifest(paired_patient_count=5),
        )

        by_branch = {branch.branch_id: branch for branch in package.branches}
        self.assertEqual(by_branch["ct-pathology-pairing"].workflow_id, "ct_pathology_fusion")

        pairing_bundle = output_dir / "branches" / "ct-pathology-pairing" / "evidence" / "evidence_bundle.json"
        payload = json.loads(pairing_bundle.read_text(encoding="utf-8"))

        self.assertEqual(payload["workflow_id"], "ct_pathology_fusion")
        self.assertIn("ct_wsi_fusion_report", payload["planned_artifacts"])
        self.assertFalse(payload["data_downloaded"])


if __name__ == "__main__":
    unittest.main()
