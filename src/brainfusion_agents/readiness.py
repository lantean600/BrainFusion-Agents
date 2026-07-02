from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import audit_dataset_registry
from .datasets import DatasetRegistry
from .ct_manifest import validate_ct_manifest
from .manifest import validate_case_selection_manifest
from .plans import build_workflow_plan
from .wsi_manifest import validate_wsi_manifest


@dataclass(frozen=True)
class PetMrReadinessReport:
    metadata_ready: bool
    dry_run_only: bool
    can_support_main_conclusion: bool
    workflow_id: str
    dataset_ids: tuple[str, ...]
    manifest_dataset_id: str | None
    manifest_record_count: int
    registry_error_count: int
    manifest_error_count: int
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    planned_qc_gates: tuple[str, ...]
    planned_artifacts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata_ready": self.metadata_ready,
            "dry_run_only": self.dry_run_only,
            "can_support_main_conclusion": self.can_support_main_conclusion,
            "workflow_id": self.workflow_id,
            "dataset_ids": list(self.dataset_ids),
            "manifest_dataset_id": self.manifest_dataset_id,
            "manifest_record_count": self.manifest_record_count,
            "registry_error_count": self.registry_error_count,
            "manifest_error_count": self.manifest_error_count,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "planned_qc_gates": list(self.planned_qc_gates),
            "planned_artifacts": list(self.planned_artifacts),
        }


@dataclass(frozen=True)
class BranchReadinessReport:
    metadata_ready: bool
    dry_run_only: bool
    can_support_extension_experiment: bool
    workflow_id: str
    dataset_ids: tuple[str, ...]
    manifest_dataset_id: str | None
    manifest_record_count: int
    registry_error_count: int
    manifest_error_count: int
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    planned_qc_gates: tuple[str, ...]
    planned_artifacts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata_ready": self.metadata_ready,
            "dry_run_only": self.dry_run_only,
            "can_support_extension_experiment": self.can_support_extension_experiment,
            "workflow_id": self.workflow_id,
            "dataset_ids": list(self.dataset_ids),
            "manifest_dataset_id": self.manifest_dataset_id,
            "manifest_record_count": self.manifest_record_count,
            "registry_error_count": self.registry_error_count,
            "manifest_error_count": self.manifest_error_count,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "planned_qc_gates": list(self.planned_qc_gates),
            "planned_artifacts": list(self.planned_artifacts),
        }


def build_pet_mr_readiness_report(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    manifest: dict[str, Any] | str | Path,
) -> PetMrReadinessReport:
    registry_audit = audit_dataset_registry(registry)
    plan = build_workflow_plan(registry, dataset_ids)
    manifest_result = validate_case_selection_manifest(manifest)

    blockers: list[str] = []
    warnings: list[str] = []

    if registry_audit.errors:
        blockers.append("Dataset registry audit failed.")
        blockers.extend(f"{finding.dataset_id}: {finding.message}" for finding in registry_audit.errors)

    if plan.route.route != "pet_mr_mainline":
        blockers.append(f"Selected datasets route to {plan.route.route}, not pet_mr_mainline.")

    if not {"adni", "oasis-3"}.issubset(set(dataset_ids)):
        blockers.append("PET/MR readiness requires both adni and oasis-3 dataset IDs.")

    if not manifest_result.passed:
        blockers.append("Manifest validation failed.")
        blockers.extend(
            f"record {finding.record_index}: {finding.field}: {finding.message}"
            for finding in manifest_result.errors
        )

    if manifest_result.record_count == 0:
        blockers.append("Case selection manifest has no records.")

    if (
        manifest_result.dataset_id
        and manifest_result.dataset_id not in set(dataset_ids)
    ):
        blockers.append(
            f"Manifest dataset_id {manifest_result.dataset_id} is not in selected datasets."
        )

    warnings.extend(
        f"record {finding.record_index}: {finding.field}: {finding.message}"
        for finding in manifest_result.warnings
    )
    warnings.append("No imaging files were downloaded or inspected; report is metadata-only.")

    metadata_ready = not blockers

    return PetMrReadinessReport(
        metadata_ready=metadata_ready,
        dry_run_only=True,
        can_support_main_conclusion=False,
        workflow_id=plan.route.route,
        dataset_ids=tuple(dataset_ids),
        manifest_dataset_id=manifest_result.dataset_id,
        manifest_record_count=manifest_result.record_count,
        registry_error_count=registry_audit.error_count,
        manifest_error_count=manifest_result.error_count,
        blocking_reasons=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        planned_qc_gates=plan.qc_gates,
        planned_artifacts=plan.expected_artifacts,
    )


def build_wsi_readiness_report(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    manifest: dict[str, Any] | str | Path,
) -> BranchReadinessReport:
    return _build_branch_readiness_report(
        registry,
        dataset_ids,
        manifest,
        expected_route="wsi_preprocessing",
        manifest_validator=validate_wsi_manifest,
        empty_manifest_message="WSI preprocessing manifest has no records.",
    )


def build_ct_readiness_report(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    manifest: dict[str, Any] | str | Path,
) -> BranchReadinessReport:
    return _build_branch_readiness_report(
        registry,
        dataset_ids,
        manifest,
        expected_route="ct_branch",
        manifest_validator=validate_ct_manifest,
        empty_manifest_message="CT prototype manifest has no records.",
    )


def _build_branch_readiness_report(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    manifest: dict[str, Any] | str | Path,
    *,
    expected_route: str,
    manifest_validator,
    empty_manifest_message: str,
) -> BranchReadinessReport:
    registry_audit = audit_dataset_registry(registry)
    plan = build_workflow_plan(registry, dataset_ids)
    manifest_result = manifest_validator(manifest)

    blockers: list[str] = []
    warnings: list[str] = []

    if registry_audit.errors:
        blockers.append("Dataset registry audit failed.")
        blockers.extend(f"{finding.dataset_id}: {finding.message}" for finding in registry_audit.errors)

    if plan.route.route != expected_route:
        blockers.append(f"Selected datasets route to {plan.route.route}, not {expected_route}.")

    if not manifest_result.passed:
        blockers.append("Manifest validation failed.")
        blockers.extend(
            f"record {finding.record_index}: {finding.field}: {finding.message}"
            for finding in manifest_result.errors
        )

    if manifest_result.record_count == 0:
        blockers.append(empty_manifest_message)

    if (
        manifest_result.dataset_id
        and manifest_result.dataset_id not in set(dataset_ids)
    ):
        blockers.append(
            f"Manifest dataset_id {manifest_result.dataset_id} is not in selected datasets."
        )

    warnings.extend(
        f"record {finding.record_index}: {finding.field}: {finding.message}"
        for finding in manifest_result.warnings
    )
    warnings.append("No imaging files were downloaded or inspected; report is metadata-only.")

    return BranchReadinessReport(
        metadata_ready=not blockers,
        dry_run_only=True,
        can_support_extension_experiment=False,
        workflow_id=plan.route.route,
        dataset_ids=tuple(dataset_ids),
        manifest_dataset_id=manifest_result.dataset_id,
        manifest_record_count=manifest_result.record_count,
        registry_error_count=registry_audit.error_count,
        manifest_error_count=manifest_result.error_count,
        blocking_reasons=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        planned_qc_gates=plan.qc_gates,
        planned_artifacts=plan.expected_artifacts,
    )
