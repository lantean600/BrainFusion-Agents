from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import RegistryAuditResult, audit_dataset_registry
from .datasets import DatasetRegistry
from .pairing_manifest import PairingManifestValidationResult, validate_pairing_manifest
from .plans import WorkflowPlan, build_workflow_plan
from .readiness import (
    BranchReadinessReport,
    PetMrReadinessReport,
    build_ct_readiness_report,
    build_pet_mr_readiness_report,
    build_wsi_readiness_report,
)


DEFAULT_PET_MR_DATASETS = ("adni", "oasis-3")
DEFAULT_WSI_DATASETS = ("tcga-gdc-wsi", "camelyon")
DEFAULT_CT_DATASETS = ("lidc-idri", "nsclc-radiomics")
DEFAULT_CT_WSI_PAIRING_DATASETS = ("tcia-tcga-paired-candidates",)


ManifestInput = dict[str, Any] | str | Path | None


@dataclass(frozen=True)
class ProjectBranchStatus:
    branch_id: str
    workflow_id: str
    route_claim_level: str
    dataset_ids: tuple[str, ...]
    manifest_type: str
    manifest_required: bool
    manifest_provided: bool
    metadata_ready: bool
    claim_supported: bool
    dry_run_only: bool
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    planned_qc_gates: tuple[str, ...]
    planned_artifacts: tuple[str, ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "workflow_id": self.workflow_id,
            "route_claim_level": self.route_claim_level,
            "dataset_ids": list(self.dataset_ids),
            "manifest_type": self.manifest_type,
            "manifest_required": self.manifest_required,
            "manifest_provided": self.manifest_provided,
            "metadata_ready": self.metadata_ready,
            "claim_supported": self.claim_supported,
            "dry_run_only": self.dry_run_only,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "planned_qc_gates": list(self.planned_qc_gates),
            "planned_artifacts": list(self.planned_artifacts),
            "details": self.details,
        }


@dataclass(frozen=True)
class ProjectStatusReport:
    release_stage: str
    cloud_runnable: bool
    dry_run_only: bool
    data_downloaded: bool
    no_download_enforced: bool
    registry_passed: bool
    registry_error_count: int
    registry_warning_count: int
    pet_mr_mvp_metadata_ready: bool
    publishable_main_conclusion_supported: bool
    extension_experiment_supported: bool
    cloud_blockers: tuple[str, ...]
    metadata_blockers: tuple[str, ...]
    registry: RegistryAuditResult
    branches: tuple[ProjectBranchStatus, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_stage": self.release_stage,
            "cloud_runnable": self.cloud_runnable,
            "dry_run_only": self.dry_run_only,
            "data_downloaded": self.data_downloaded,
            "no_download_enforced": self.no_download_enforced,
            "registry_passed": self.registry_passed,
            "registry_error_count": self.registry_error_count,
            "registry_warning_count": self.registry_warning_count,
            "pet_mr_mvp_metadata_ready": self.pet_mr_mvp_metadata_ready,
            "publishable_main_conclusion_supported": self.publishable_main_conclusion_supported,
            "extension_experiment_supported": self.extension_experiment_supported,
            "cloud_blockers": list(self.cloud_blockers),
            "metadata_blockers": list(self.metadata_blockers),
            "registry": self.registry.to_dict(),
            "branches": [branch.to_dict() for branch in self.branches],
        }


def build_project_status_report(
    registry: DatasetRegistry,
    *,
    pet_mr_manifest: ManifestInput = None,
    wsi_manifest: ManifestInput = None,
    ct_manifest: ManifestInput = None,
    pairing_manifest: ManifestInput = None,
    pet_mr_dataset_ids: tuple[str, ...] = DEFAULT_PET_MR_DATASETS,
    wsi_dataset_ids: tuple[str, ...] = DEFAULT_WSI_DATASETS,
    ct_dataset_ids: tuple[str, ...] = DEFAULT_CT_DATASETS,
    ct_wsi_pairing_dataset_ids: tuple[str, ...] = DEFAULT_CT_WSI_PAIRING_DATASETS,
) -> ProjectStatusReport:
    registry_audit = audit_dataset_registry(registry)
    data_downloaded = any(record.access_status == "downloaded" for record in registry.list())

    branches = (
        _pet_mr_branch(registry, pet_mr_dataset_ids, pet_mr_manifest),
        _wsi_branch(registry, wsi_dataset_ids, wsi_manifest),
        _ct_branch(registry, ct_dataset_ids, ct_manifest),
        _pairing_branch(registry, ct_wsi_pairing_dataset_ids, pairing_manifest),
    )

    no_download_enforced = not data_downloaded and all(branch.dry_run_only for branch in branches)
    cloud_blockers: list[str] = []
    if not registry_audit.passed:
        cloud_blockers.append("Dataset registry audit failed.")
    if data_downloaded:
        cloud_blockers.append("At least one dataset is marked downloaded; cloud dry-run mode requires links only.")
    if not no_download_enforced:
        cloud_blockers.append("No-download enforcement failed.")

    metadata_blockers = tuple(
        dict.fromkeys(
            f"{branch.branch_id}: {reason}"
            for branch in branches
            for reason in branch.blocking_reasons
        )
    )

    pet_mr_branch = branches[0]
    extension_branches = branches[1:]

    return ProjectStatusReport(
        release_stage="metadata-dry-run",
        cloud_runnable=not cloud_blockers,
        dry_run_only=True,
        data_downloaded=data_downloaded,
        no_download_enforced=no_download_enforced,
        registry_passed=registry_audit.passed,
        registry_error_count=registry_audit.error_count,
        registry_warning_count=registry_audit.warning_count,
        pet_mr_mvp_metadata_ready=pet_mr_branch.metadata_ready,
        publishable_main_conclusion_supported=False,
        extension_experiment_supported=any(branch.claim_supported for branch in extension_branches),
        cloud_blockers=tuple(dict.fromkeys(cloud_blockers)),
        metadata_blockers=metadata_blockers,
        registry=registry_audit,
        branches=branches,
    )


def _pet_mr_branch(
    registry: DatasetRegistry,
    dataset_ids: tuple[str, ...],
    manifest: ManifestInput,
) -> ProjectBranchStatus:
    if manifest is None:
        plan = build_workflow_plan(registry, dataset_ids)
        return _missing_manifest_branch(
            "pet-mr-mvp",
            "pet_mr_case_selection",
            "PET/MR case selection manifest was not provided.",
            plan,
        )

    report = build_pet_mr_readiness_report(registry, dataset_ids, manifest)
    return _branch_from_pet_mr_readiness("pet-mr-mvp", "pet_mr_case_selection", report)


def _wsi_branch(
    registry: DatasetRegistry,
    dataset_ids: tuple[str, ...],
    manifest: ManifestInput,
) -> ProjectBranchStatus:
    if manifest is None:
        plan = build_workflow_plan(registry, dataset_ids)
        return _missing_manifest_branch(
            "wsi-preprocessing",
            "wsi_preprocessing",
            "WSI preprocessing manifest was not provided.",
            plan,
        )

    report = build_wsi_readiness_report(registry, dataset_ids, manifest)
    return _branch_from_readiness("wsi-preprocessing", "wsi_preprocessing", report)


def _ct_branch(
    registry: DatasetRegistry,
    dataset_ids: tuple[str, ...],
    manifest: ManifestInput,
) -> ProjectBranchStatus:
    if manifest is None:
        plan = build_workflow_plan(registry, dataset_ids)
        return _missing_manifest_branch(
            "ct-prototype",
            "ct_prototype",
            "CT prototype manifest was not provided.",
            plan,
        )

    report = build_ct_readiness_report(registry, dataset_ids, manifest)
    return _branch_from_readiness("ct-prototype", "ct_prototype", report)


def _pairing_branch(
    registry: DatasetRegistry,
    dataset_ids: tuple[str, ...],
    manifest: ManifestInput,
) -> ProjectBranchStatus:
    if manifest is None:
        plan = build_workflow_plan(registry, dataset_ids)
        return _missing_manifest_branch(
            "ct-pathology-pairing",
            "ct_pathology_pairing_audit",
            "CT-pathology pairing audit manifest was not provided.",
            plan,
        )

    result = validate_pairing_manifest(manifest)
    pairing_verified = result.passed
    pairing_level = result.pairing_level if result.passed else "none"
    plan = build_workflow_plan(
        registry,
        dataset_ids,
        pairing_verified=pairing_verified,
        pairing_level=pairing_level,
    )
    blockers = _pairing_blockers(result)
    warnings = tuple(_format_manifest_finding(finding) for finding in result.warnings)
    warnings = warnings + ("No imaging files were downloaded or inspected; report is metadata-only.",)

    return ProjectBranchStatus(
        branch_id="ct-pathology-pairing",
        workflow_id=plan.route.route,
        route_claim_level=plan.route.claim_level,
        dataset_ids=tuple(dataset_ids),
        manifest_type="ct_pathology_pairing_audit",
        manifest_required=True,
        manifest_provided=True,
        metadata_ready=not blockers,
        claim_supported=False,
        dry_run_only=True,
        blocking_reasons=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        planned_qc_gates=plan.qc_gates,
        planned_artifacts=plan.expected_artifacts,
        details={
            "gate_status": result.gate_status,
            "pairing_level": result.pairing_level,
            "paired_patient_count": result.paired_patient_count,
            "paired_lesion_count": result.paired_lesion_count,
        },
    )


def _missing_manifest_branch(
    branch_id: str,
    manifest_type: str,
    missing_message: str,
    plan: WorkflowPlan,
) -> ProjectBranchStatus:
    return ProjectBranchStatus(
        branch_id=branch_id,
        workflow_id=plan.route.route,
        route_claim_level=plan.route.claim_level,
        dataset_ids=plan.dataset_ids,
        manifest_type=manifest_type,
        manifest_required=True,
        manifest_provided=False,
        metadata_ready=False,
        claim_supported=False,
        dry_run_only=True,
        blocking_reasons=(missing_message,),
        warnings=("No imaging files were downloaded or inspected; report is metadata-only.",),
        planned_qc_gates=plan.qc_gates,
        planned_artifacts=plan.expected_artifacts,
        details={},
    )


def _branch_from_pet_mr_readiness(
    branch_id: str,
    manifest_type: str,
    report: PetMrReadinessReport,
) -> ProjectBranchStatus:
    return ProjectBranchStatus(
        branch_id=branch_id,
        workflow_id=report.workflow_id,
        route_claim_level=_claim_level_for_workflow(report.workflow_id),
        dataset_ids=report.dataset_ids,
        manifest_type=manifest_type,
        manifest_required=True,
        manifest_provided=True,
        metadata_ready=report.metadata_ready,
        claim_supported=report.can_support_main_conclusion,
        dry_run_only=report.dry_run_only,
        blocking_reasons=report.blocking_reasons,
        warnings=report.warnings,
        planned_qc_gates=report.planned_qc_gates,
        planned_artifacts=report.planned_artifacts,
        details={
            "manifest_dataset_id": report.manifest_dataset_id,
            "manifest_record_count": report.manifest_record_count,
            "manifest_error_count": report.manifest_error_count,
        },
    )


def _branch_from_readiness(
    branch_id: str,
    manifest_type: str,
    report: BranchReadinessReport,
) -> ProjectBranchStatus:
    return ProjectBranchStatus(
        branch_id=branch_id,
        workflow_id=report.workflow_id,
        route_claim_level=_claim_level_for_workflow(report.workflow_id),
        dataset_ids=report.dataset_ids,
        manifest_type=manifest_type,
        manifest_required=True,
        manifest_provided=True,
        metadata_ready=report.metadata_ready,
        claim_supported=report.can_support_extension_experiment,
        dry_run_only=report.dry_run_only,
        blocking_reasons=report.blocking_reasons,
        warnings=report.warnings,
        planned_qc_gates=report.planned_qc_gates,
        planned_artifacts=report.planned_artifacts,
        details={
            "manifest_dataset_id": report.manifest_dataset_id,
            "manifest_record_count": report.manifest_record_count,
            "manifest_error_count": report.manifest_error_count,
        },
    )


def _pairing_blockers(result: PairingManifestValidationResult) -> tuple[str, ...]:
    blockers: list[str] = []
    if not result.passed:
        blockers.append("CT-pathology pairing gate did not pass.")
    blockers.extend(_format_manifest_finding(finding) for finding in result.errors)
    return tuple(dict.fromkeys(blockers))


def _format_manifest_finding(finding: Any) -> str:
    if finding.record_index is None:
        return f"{finding.field}: {finding.message}"
    return f"record {finding.record_index}: {finding.field}: {finding.message}"


def _claim_level_for_workflow(workflow_id: str) -> str:
    claim_levels = {
        "pet_mr_mainline": "main-conclusion-eligible",
        "pet_only_baseline": "baseline-evidence-only",
        "mr_only_baseline": "baseline-evidence-only",
        "wsi_preprocessing": "extension-preprocessing-evidence",
        "ct_branch": "extension-prototype-evidence",
        "ct_wsi_separate_with_pairing_audit": "no-fusion-claim",
        "ct_pathology_fusion": "formal-extension-eligible",
    }
    return claim_levels.get(workflow_id, "no-claim")
