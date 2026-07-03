import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path | None = None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "brainfusion_agents", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or PROJECT_ROOT),
    )


class CliTests(unittest.TestCase):
    def test_route_command_outputs_pet_mr_mainline(self) -> None:
        completed = run_cli("route", "--modalities", "PET", "MR")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["route"], "pet_mr_mainline")
        self.assertEqual(payload["claim_level"], "main-conclusion-eligible")

    def test_datasets_command_filters_by_modality_without_downloads(self) -> None:
        completed = run_cli("datasets", "--modality", "PET")

        payload = json.loads(completed.stdout)
        ids = {record["dataset_id"] for record in payload}

        self.assertIn("adni", ids)
        self.assertIn("oasis-3", ids)
        self.assertTrue(all(record["access_status"] != "downloaded" for record in payload))

    def test_audit_registry_command_passes_current_registry(self) -> None:
        completed = run_cli("audit-registry")

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["error_count"], 0)
        self.assertIn("adni", payload["dataset_ids"])

    def test_project_status_command_reports_cloud_dry_run_without_manifests(self) -> None:
        completed = run_cli("project-status")

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["cloud_runnable"])
        self.assertTrue(payload["dry_run_only"])
        self.assertFalse(payload["data_downloaded"])
        self.assertFalse(payload["pet_mr_mvp_metadata_ready"])
        self.assertEqual(payload["release_stage"], "metadata-dry-run")
        self.assertEqual(len(payload["branches"]), 4)

    def test_project_status_command_uses_bundled_registry_outside_repo_root(self) -> None:
        cwd = PROJECT_ROOT / "test-output" / f"outside-repo-{uuid.uuid4().hex}"
        cwd.mkdir(parents=True, exist_ok=True)

        completed = run_cli("project-status", cwd=cwd)

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["registry_passed"])
        self.assertTrue(payload["cloud_runnable"])
        self.assertIn("adni", payload["registry"]["dataset_ids"])

    def test_project_status_command_accepts_pet_mr_manifest(self) -> None:
        path = Path("test-output") / f"cli-project-status-pet-mr-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli("project-status", "--pet-mr-manifest", str(path))

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["cloud_runnable"])
        self.assertTrue(payload["pet_mr_mvp_metadata_ready"])
        self.assertFalse(payload["publishable_main_conclusion_supported"])

    def test_materialize_project_dry_run_command_writes_project_package(self) -> None:
        output_dir = Path("test-output") / f"cli-project-dry-run-{uuid.uuid4().hex}"

        completed = run_cli(
            "materialize-project-dry-run",
            "--output-dir",
            str(output_dir),
        )

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["package_root"], str(output_dir))
        self.assertTrue(payload["cloud_runnable"])
        self.assertTrue(payload["dry_run_only"])
        self.assertTrue((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "project_status.json").exists())
        self.assertEqual(len(payload["branches"]), 4)

    def test_validate_project_package_command_accepts_cloud_run_package(self) -> None:
        output_dir = Path("test-output") / f"cli-package-validation-{uuid.uuid4().hex}"
        run_cli("cloud-run", "--output-dir", str(output_dir))

        completed = run_cli(
            "validate-project-package",
            "--package-dir",
            str(output_dir),
        )

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["branch_count"], 4)
        self.assertEqual(payload["error_count"], 0)

    def test_run_pipeline_command_writes_preprocessing_and_fusion_package(self) -> None:
        output_dir = Path("test-output") / f"cli-pipeline-{uuid.uuid4().hex}"

        completed = run_cli("run-pipeline", "--output-dir", str(output_dir))

        payload = json.loads(completed.stdout)
        report = json.loads((output_dir / "pipeline_report.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["output_dir"], str(output_dir))
        self.assertTrue(payload["dry_run_only"])
        self.assertFalse(payload["data_downloaded"])
        self.assertEqual(report["branch_count"], 4)
        self.assertTrue((output_dir / "artifacts" / "pet-mr-fusion" / "pet_mr_fusion_planning.json").exists())

    def test_cloud_run_command_writes_project_package_with_sample_manifests(self) -> None:
        output_dir = Path("test-output") / f"cli-cloud-run-{uuid.uuid4().hex}"

        completed = run_cli(
            "cloud-run",
            "--output-dir",
            str(output_dir),
        )

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["package_root"], str(output_dir))
        self.assertTrue(payload["cloud_runnable"])
        self.assertTrue(payload["dry_run_only"])
        self.assertTrue((output_dir / "manifest.json").exists())

        status = json.loads((output_dir / "project_status.json").read_text(encoding="utf-8"))
        self.assertTrue(status["pet_mr_mvp_metadata_ready"])

    def test_cloud_job_command_writes_project_pipeline_and_summary_outputs(self) -> None:
        output_dir = Path("test-output") / f"cli-cloud-job-{uuid.uuid4().hex}"

        completed = run_cli(
            "cloud-job",
            "--output-dir",
            str(output_dir),
            "--download-policy",
            "off",
        )

        payload = json.loads(completed.stdout)
        summary = json.loads((output_dir / "job_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["output_dir"], str(output_dir))
        self.assertTrue(payload["cloud_runnable"])
        self.assertTrue(payload["project_package_validation"]["passed"])
        self.assertTrue(summary["cloud_runnable"])
        self.assertEqual(summary["pipeline_branch_count"], 4)
        self.assertTrue((output_dir / "project-dry-run" / "manifest.json").exists())
        self.assertTrue((output_dir / "pipeline-run" / "pipeline_report.json").exists())
        self.assertTrue((output_dir / "synthetic-runtime" / "demo_summary.json").exists())

    def test_cloud_job_command_finds_sample_manifests_outside_repo_root(self) -> None:
        cwd = PROJECT_ROOT / "test-output" / f"cloud-job-outside-repo-{uuid.uuid4().hex}"
        output_dir = cwd / "cloud-output"
        cwd.mkdir(parents=True, exist_ok=True)

        completed = run_cli(
            "cloud-job",
            "--output-dir",
            str(output_dir),
            "--download-policy",
            "off",
            cwd=cwd,
        )

        payload = json.loads(completed.stdout)
        summary = json.loads((output_dir / "job_summary.json").read_text(encoding="utf-8"))

        self.assertTrue(payload["cloud_runnable"])
        self.assertEqual(summary["ready_pipeline_branches"], ["pet-mr-fusion", "wsi-preprocessing", "ct-preprocessing"])

    def test_download_data_command_writes_tumor_plan_without_network(self) -> None:
        output_dir = Path("test-output") / f"cli-download-plan-{uuid.uuid4().hex}"

        completed = run_cli(
            "download-data",
            "--output-dir",
            str(output_dir),
            "--dataset-ids",
            "medmnist-breastmnist",
        )

        payload = json.loads(completed.stdout)
        summary = json.loads((output_dir / "download_summary.json").read_text(encoding="utf-8"))

        self.assertFalse(payload["data_downloaded"])
        self.assertEqual(summary["selected_dataset_ids"], ["medmnist-breastmnist"])
        self.assertEqual(summary["planned_count"], 1)
        self.assertTrue((output_dir / "download_manifest.json").exists())

    def test_synthetic_demo_command_writes_runtime_outputs(self) -> None:
        output_dir = Path("test-output") / f"cli-synthetic-demo-{uuid.uuid4().hex}"

        completed = run_cli(
            "synthetic-demo",
            "--output-dir",
            str(output_dir),
            "--subject-count",
            "2",
            "--seed",
            "7",
        )

        payload = json.loads(completed.stdout)
        summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["output_dir"], str(output_dir))
        self.assertTrue(payload["synthetic_data"])
        self.assertFalse(payload["data_downloaded"])
        self.assertEqual(summary["pet_mr_fusion_records"], 2)
        self.assertTrue((output_dir / "pet_mr_fusion_demo.json").exists())

    def test_cloud_run_command_finds_sample_manifests_outside_repo_root(self) -> None:
        cwd = PROJECT_ROOT / "test-output" / f"cloud-run-outside-repo-{uuid.uuid4().hex}"
        output_dir = cwd / "cloud-output"
        cwd.mkdir(parents=True, exist_ok=True)

        completed = run_cli(
            "cloud-run",
            "--output-dir",
            str(output_dir),
            cwd=cwd,
        )

        payload = json.loads(completed.stdout)
        status = json.loads((output_dir / "project_status.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["package_root"], str(output_dir))
        self.assertTrue(status["pet_mr_mvp_metadata_ready"])

    def test_cloud_run_command_can_skip_sample_manifests(self) -> None:
        output_dir = Path("test-output") / f"cli-cloud-run-no-samples-{uuid.uuid4().hex}"

        completed = run_cli(
            "cloud-run",
            "--output-dir",
            str(output_dir),
            "--no-sample-manifests",
        )

        payload = json.loads(completed.stdout)
        status = json.loads((output_dir / "project_status.json").read_text(encoding="utf-8"))

        self.assertTrue(payload["cloud_runnable"])
        self.assertFalse(status["pet_mr_mvp_metadata_ready"])
        self.assertIn(
            "pet-mr-mvp: PET/MR case selection manifest was not provided.",
            status["metadata_blockers"],
        )

    def test_manifest_template_command_outputs_no_download_template(self) -> None:
        completed = run_cli("manifest-template")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["manifest_type"], "pet_mr_case_selection")
        self.assertIn("required_record_fields", payload)
        self.assertNotIn("local_path", completed.stdout)

    def test_validate_manifest_command_accepts_empty_template_file(self) -> None:
        path = Path("test-output") / f"cli-manifest-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "manifest_type": "pet_mr_case_selection",
                    "dataset_id": "adni",
                    "records": [],
                }
            ),
            encoding="utf-8",
        )

        completed = run_cli("validate-manifest", "--manifest", str(path))

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["record_count"], 0)

    def test_pairing_manifest_template_command_outputs_no_download_template(self) -> None:
        completed = run_cli("pairing-manifest-template")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["manifest_type"], "ct_pathology_pairing_audit")
        self.assertIn("source_datasets", payload)
        self.assertNotIn("local_path", completed.stdout)

    def test_validate_pairing_manifest_command_reports_failed_gate(self) -> None:
        path = Path("test-output") / f"cli-pairing-manifest-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "manifest_type": "ct_pathology_pairing_audit",
                    "source_datasets": ["tcia", "tcga-gdc"],
                    "identifier_fields": [],
                    "paired_patient_count": 0,
                    "paired_lesion_count": None,
                    "timing_assumption": "",
                    "endpoint_available": False,
                    "evidence": [],
                }
            ),
            encoding="utf-8",
        )

        completed = run_cli("validate-pairing-manifest", "--manifest", str(path))

        payload = json.loads(completed.stdout)

        self.assertFalse(payload["passed"])
        self.assertEqual(payload["gate_status"], "fail")

    def test_wsi_manifest_template_command_outputs_no_download_template(self) -> None:
        completed = run_cli("wsi-manifest-template")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["manifest_type"], "wsi_preprocessing")
        self.assertIn("required_record_fields", payload)
        self.assertNotIn("slide_path", completed.stdout)

    def test_validate_wsi_manifest_command_accepts_valid_manifest(self) -> None:
        path = Path("test-output") / f"cli-wsi-manifest-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli("validate-wsi-manifest", "--manifest", str(path))

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["record_count"], 1)

    def test_ct_manifest_template_command_outputs_no_download_template(self) -> None:
        completed = run_cli("ct-manifest-template")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["manifest_type"], "ct_prototype")
        self.assertIn("required_record_fields", payload)
        self.assertNotIn("dicom_path", completed.stdout)

    def test_validate_ct_manifest_command_accepts_valid_manifest(self) -> None:
        path = Path("test-output") / f"cli-ct-manifest-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli("validate-ct-manifest", "--manifest", str(path))

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["passed"])
        self.assertEqual(payload["record_count"], 1)

    def test_pet_mr_readiness_command_reports_metadata_ready(self) -> None:
        path = Path("test-output") / f"cli-readiness-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli(
            "pet-mr-readiness",
            "--dataset-ids",
            "adni",
            "oasis-3",
            "--manifest",
            str(path),
        )

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["metadata_ready"])
        self.assertTrue(payload["dry_run_only"])
        self.assertFalse(payload["can_support_main_conclusion"])

    def test_wsi_readiness_command_reports_metadata_ready(self) -> None:
        path = Path("test-output") / f"cli-wsi-readiness-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli(
            "wsi-readiness",
            "--dataset-ids",
            "tcga-gdc-wsi",
            "camelyon",
            "--manifest",
            str(path),
        )

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["metadata_ready"])
        self.assertEqual(payload["workflow_id"], "wsi_preprocessing")
        self.assertFalse(payload["can_support_extension_experiment"])

    def test_ct_readiness_command_reports_metadata_ready(self) -> None:
        path = Path("test-output") / f"cli-ct-readiness-{uuid.uuid4().hex}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )

        completed = run_cli(
            "ct-readiness",
            "--dataset-ids",
            "lidc-idri",
            "nsclc-radiomics",
            "--manifest",
            str(path),
        )

        payload = json.loads(completed.stdout)

        self.assertTrue(payload["metadata_ready"])
        self.assertEqual(payload["workflow_id"], "ct_branch")
        self.assertFalse(payload["can_support_extension_experiment"])

    def test_pairing_gate_command_fails_without_patient_pairing(self) -> None:
        completed = run_cli("pairing-gate", "--sources", "tcia", "tcga-gdc")

        payload = json.loads(completed.stdout)

        self.assertFalse(payload["passed"])
        self.assertEqual(payload["pairing_level"], "none")

    def test_plan_datasets_command_outputs_gates_and_blocks_downloads(self) -> None:
        completed = run_cli("plan-datasets", "--dataset-ids", "adni", "oasis-3")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["route"]["route"], "pet_mr_mainline")
        self.assertTrue(payload["downloads_blocked"])
        self.assertIn("subject_session_alignment", payload["qc_gates"])
        self.assertIn("agent_trace_bundle", payload["expected_artifacts"])

    def test_dry_run_evidence_command_outputs_planned_bundle_without_downloads(self) -> None:
        completed = run_cli("dry-run-evidence", "--dataset-ids", "adni", "oasis-3")

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["workflow_id"], "pet_mr_mainline")
        self.assertFalse(payload["data_downloaded"])
        self.assertTrue(payload["downloads_blocked"])
        self.assertIn("agent_trace_bundle", payload["planned_artifacts"])
        self.assertGreaterEqual(len(payload["traces"]), 1)

    def test_dry_run_evidence_command_blocks_unpaired_ct_wsi_fusion_artifact(self) -> None:
        completed = run_cli(
            "dry-run-evidence",
            "--dataset-ids",
            "lidc-idri",
            "tcga-gdc-wsi",
        )

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["workflow_id"], "ct_wsi_separate_with_pairing_audit")
        self.assertIn("pairing_audit_report", payload["planned_artifacts"])
        self.assertNotIn("ct_wsi_fusion_report", payload["planned_artifacts"])

    def test_materialize_dry_run_command_writes_package(self) -> None:
        output_dir = Path("test-output") / f"cli-materialize-{uuid.uuid4().hex}"

        completed = run_cli(
            "materialize-dry-run",
            "--dataset-ids",
            "adni",
            "oasis-3",
            "--output-dir",
            str(output_dir),
        )

        payload = json.loads(completed.stdout)

        self.assertEqual(payload["package_root"], str(output_dir))
        self.assertTrue((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "evidence_bundle.json").exists())
        self.assertTrue((output_dir / "artifacts" / "agent_trace_bundle.json").exists())


if __name__ == "__main__":
    unittest.main()
