from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ct_manifest import validate_ct_manifest
from .datasets import DatasetRegistry
from .manifest import validate_case_selection_manifest
from .pairing_manifest import validate_pairing_manifest
from .readiness import (
    build_ct_readiness_report,
    build_pet_mr_readiness_report,
    build_wsi_readiness_report,
)
from .wsi_manifest import validate_wsi_manifest


PET_MR_DATASETS = ("adni", "oasis-3")
WSI_DATASETS = ("tcga-gdc-wsi", "camelyon")
CT_DATASETS = ("lidc-idri", "nsclc-radiomics")
PAIRING_DATASETS = ("tcia-tcga-paired-candidates",)


@dataclass(frozen=True)
class PipelineTaskResult:
    task_id: str
    branch_id: str
    status: str
    input_refs: tuple[str, ...]
    output_artifacts: tuple[str, ...]
    qc_gates: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "branch_id": self.branch_id,
            "status": self.status,
            "input_refs": list(self.input_refs),
            "output_artifacts": list(self.output_artifacts),
            "qc_gates": list(self.qc_gates),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PipelineBranchResult:
    branch_id: str
    workflow_id: str
    status: str
    dataset_ids: tuple[str, ...]
    manifest_record_count: int
    tasks: tuple[PipelineTaskResult, ...]
    artifacts: tuple[str, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "dataset_ids": list(self.dataset_ids),
            "manifest_record_count": self.manifest_record_count,
            "tasks": [task.to_dict() for task in self.tasks],
            "artifacts": list(self.artifacts),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class PipelineRunResult:
    release_stage: str
    dry_run_only: bool
    data_downloaded: bool
    branch_count: int
    branches: tuple[PipelineBranchResult, ...]
    artifacts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_stage": self.release_stage,
            "dry_run_only": self.dry_run_only,
            "data_downloaded": self.data_downloaded,
            "branch_count": self.branch_count,
            "branches": [branch.to_dict() for branch in self.branches],
            "artifacts": list(self.artifacts),
        }


@dataclass(frozen=True)
class MaterializedPipelineRun:
    output_dir: Path
    report: PipelineRunResult
    files: tuple[Path, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "dry_run_only": self.report.dry_run_only,
            "data_downloaded": self.report.data_downloaded,
            "branch_count": self.report.branch_count,
            "files": [str(path) for path in self.files],
        }


def build_pipeline_run(
    registry: DatasetRegistry,
    *,
    pet_mr_manifest: str | Path | dict[str, Any] | None = None,
    wsi_manifest: str | Path | dict[str, Any] | None = None,
    ct_manifest: str | Path | dict[str, Any] | None = None,
    pairing_manifest: str | Path | dict[str, Any] | None = None,
) -> PipelineRunResult:
    branches = (
        _pet_mr_branch(registry, pet_mr_manifest),
        _wsi_branch(registry, wsi_manifest),
        _ct_branch(registry, ct_manifest),
        _pairing_branch(registry, pairing_manifest),
    )
    artifacts = tuple(artifact for branch in branches for artifact in branch.artifacts)
    return PipelineRunResult(
        release_stage="pipeline-dry-run",
        dry_run_only=True,
        data_downloaded=False,
        branch_count=len(branches),
        branches=branches,
        artifacts=artifacts,
    )


def materialize_pipeline_run(
    registry: DatasetRegistry,
    output_dir: str | Path,
    *,
    pet_mr_manifest: str | Path | dict[str, Any] | None = None,
    wsi_manifest: str | Path | dict[str, Any] | None = None,
    ct_manifest: str | Path | dict[str, Any] | None = None,
    pairing_manifest: str | Path | dict[str, Any] | None = None,
) -> MaterializedPipelineRun:
    root = Path(output_dir)
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report = build_pipeline_run(
        registry,
        pet_mr_manifest=pet_mr_manifest,
        wsi_manifest=wsi_manifest,
        ct_manifest=ct_manifest,
        pairing_manifest=pairing_manifest,
    )

    files: list[Path] = []
    report_path = root / "pipeline_report.json"
    _write_json(report_path, report.to_dict())
    files.append(report_path)

    for branch in report.branches:
        branch_dir = artifacts_dir / branch.branch_id
        branch_dir.mkdir(parents=True, exist_ok=True)
        branch_path = branch_dir / "branch_report.json"
        _write_json(branch_path, branch.to_dict())
        files.append(branch_path)
        for task in branch.tasks:
            task_path = branch_dir / f"{task.task_id}.json"
            _write_json(
                task_path,
                {
                    **task.to_dict(),
                    "dry_run_only": True,
                    "data_downloaded": False,
                    "downloads_blocked": True,
                },
            )
            files.append(task_path)

    manifest_path = root / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "brainfusion-pipeline-run/v1",
            "release_stage": report.release_stage,
            "dry_run_only": True,
            "data_downloaded": False,
            "branch_count": report.branch_count,
            "files": [str(path.relative_to(root)) for path in files],
        },
    )
    files.insert(0, manifest_path)
    return MaterializedPipelineRun(root, report, tuple(files))


def _pet_mr_branch(
    registry: DatasetRegistry,
    manifest: str | Path | dict[str, Any] | None,
) -> PipelineBranchResult:
    if manifest is None:
        return _blocked_branch(
            "pet-mr-fusion",
            "pet_mr_mainline",
            PET_MR_DATASETS,
            ("PET/MR case selection manifest was not provided.",),
        )
    readiness = build_pet_mr_readiness_report(registry, PET_MR_DATASETS, manifest)
    validation = validate_case_selection_manifest(manifest)
    artifacts = (
        "pet_preprocessing_plan",
        "mr_preprocessing_plan",
        "subject_session_alignment_report",
        "pet_only_baseline_plan",
        "mr_only_baseline_plan",
        "pet_mr_fusion_plan",
        "fusion_qc_report",
    )
    tasks = _tasks(
        "pet-mr-fusion",
        "ready" if readiness.metadata_ready else "blocked",
        (
            ("pet_qc", ("pet_presence", "pet_qc_status")),
            ("mr_qc", ("mr_presence", "mr_qc_status")),
            ("subject_session_alignment", ("subject_session_alignment",)),
            ("pet_mr_fusion_planning", ("preprocessing_compatibility", "trace_completeness")),
        ),
        artifacts,
        ("source manifest records only; no PET/MR files inspected.",),
    )
    return PipelineBranchResult(
        "pet-mr-fusion",
        readiness.workflow_id,
        "ready" if readiness.metadata_ready else "blocked",
        readiness.dataset_ids,
        validation.record_count,
        tasks,
        artifacts,
        readiness.blocking_reasons,
    )


def _wsi_branch(
    registry: DatasetRegistry,
    manifest: str | Path | dict[str, Any] | None,
) -> PipelineBranchResult:
    if manifest is None:
        return _blocked_branch(
            "wsi-preprocessing",
            "wsi_preprocessing",
            WSI_DATASETS,
            ("WSI preprocessing manifest was not provided.",),
        )
    readiness = build_wsi_readiness_report(registry, WSI_DATASETS, manifest)
    validation = validate_wsi_manifest(manifest)
    artifacts = (
        "slide_inventory",
        "tissue_detection_plan",
        "artifact_filtering_plan",
        "stain_normalization_plan",
        "patch_extraction_plan",
        "wsi_embedding_plan",
    )
    tasks = _tasks(
        "wsi-preprocessing",
        "ready" if readiness.metadata_ready else "blocked",
        (
            ("slide_qc", ("slide_readable",)),
            ("tissue_detection", ("tissue_detection",)),
            ("artifact_filtering", ("artifact_filtering",)),
            ("patch_and_embedding_planning", ("patch_extraction", "embedding_extraction")),
        ),
        artifacts,
        ("source slide identifiers only; no WSI tiles or embeddings generated.",),
    )
    return PipelineBranchResult(
        "wsi-preprocessing",
        readiness.workflow_id,
        "ready" if readiness.metadata_ready else "blocked",
        readiness.dataset_ids,
        validation.record_count,
        tasks,
        artifacts,
        readiness.blocking_reasons,
    )


def _ct_branch(
    registry: DatasetRegistry,
    manifest: str | Path | dict[str, Any] | None,
) -> PipelineBranchResult:
    if manifest is None:
        return _blocked_branch(
            "ct-preprocessing",
            "ct_branch",
            CT_DATASETS,
            ("CT prototype manifest was not provided.",),
        )
    readiness = build_ct_readiness_report(registry, CT_DATASETS, manifest)
    validation = validate_ct_manifest(manifest)
    artifacts = (
        "ct_series_inventory",
        "ct_metadata_qc_report",
        "annotation_readiness_report",
        "ct_feature_extraction_plan",
        "ct_baseline_plan",
    )
    tasks = _tasks(
        "ct-preprocessing",
        "ready" if readiness.metadata_ready else "blocked",
        (
            ("ct_series_qc", ("ct_series_readable",)),
            ("ct_metadata_qc", ("ct_metadata_sufficient",)),
            ("annotation_check", ("annotation_availability",)),
            ("ct_baseline_planning", ("baseline_output_generated", "trace_completeness")),
        ),
        artifacts,
        ("source CT identifiers only; no DICOM files inspected.",),
    )
    return PipelineBranchResult(
        "ct-preprocessing",
        readiness.workflow_id,
        "ready" if readiness.metadata_ready else "blocked",
        readiness.dataset_ids,
        validation.record_count,
        tasks,
        artifacts,
        readiness.blocking_reasons,
    )


def _pairing_branch(
    registry: DatasetRegistry,
    manifest: str | Path | dict[str, Any] | None,
) -> PipelineBranchResult:
    del registry
    if manifest is None:
        return _blocked_branch(
            "ct-wsi-pairing",
            "ct_wsi_separate_with_pairing_audit",
            PAIRING_DATASETS,
            ("CT-pathology pairing audit manifest was not provided.",),
        )
    validation = validate_pairing_manifest(manifest)
    workflow_id = "ct_pathology_fusion" if validation.passed else "ct_wsi_separate_with_pairing_audit"
    status = "ready" if validation.passed else "blocked"
    artifacts = (
        "pairing_audit_report",
        "ct_wsi_fusion_plan" if validation.passed else "ct_wsi_fusion_blocker_report",
        "missing_modality_policy",
    )
    tasks = _tasks(
        "ct-wsi-pairing",
        status,
        (
            ("pairing_gate", ("pairing_evidence_collected", "pairing_gate_evaluated")),
            ("fusion_gate_routing", ("missing_modality_reported", "trace_completeness")),
        ),
        artifacts,
        ("cross-scale fusion remains gated by verified patient-level or lesion-level pairing.",),
    )
    blockers = tuple(finding.message for finding in validation.errors)
    if not validation.passed and "CT-pathology pairing gate did not pass." not in blockers:
        blockers = ("CT-pathology pairing gate did not pass.",) + blockers
    return PipelineBranchResult(
        "ct-wsi-pairing",
        workflow_id,
        status,
        PAIRING_DATASETS,
        validation.paired_patient_count,
        tasks,
        artifacts,
        blockers,
    )


def _blocked_branch(
    branch_id: str,
    workflow_id: str,
    dataset_ids: tuple[str, ...],
    blockers: tuple[str, ...],
) -> PipelineBranchResult:
    return PipelineBranchResult(
        branch_id,
        workflow_id,
        "blocked",
        dataset_ids,
        0,
        (),
        (),
        blockers,
    )


def _tasks(
    branch_id: str,
    status: str,
    task_specs: tuple[tuple[str, tuple[str, ...]], ...],
    artifacts: tuple[str, ...],
    notes: tuple[str, ...],
) -> tuple[PipelineTaskResult, ...]:
    return tuple(
        PipelineTaskResult(
            task_id=task_id,
            branch_id=branch_id,
            status="planned" if status == "ready" else "blocked",
            input_refs=("manifest_records",),
            output_artifacts=artifacts,
            qc_gates=qc_gates,
            notes=notes,
        )
        for task_id, qc_gates in task_specs
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
