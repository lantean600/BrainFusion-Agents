from __future__ import annotations

from dataclasses import dataclass

from .datasets import DatasetRegistry, DatasetRecord
from .workflow import WorkflowRequest, WorkflowRoute, route_workflow


@dataclass(frozen=True)
class WorkflowPlan:
    route: WorkflowRoute
    dataset_ids: tuple[str, ...]
    dataset_names: tuple[str, ...]
    modalities: tuple[str, ...]
    qc_gates: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    trace_requirements: tuple[str, ...]
    downloads_blocked: bool = True
    notes: tuple[str, ...] = ()


def build_workflow_plan(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    *,
    pairing_verified: bool = False,
    pairing_level: str = "none",
) -> WorkflowPlan:
    records = tuple(registry.get(dataset_id) for dataset_id in dataset_ids)
    if not records:
        raise ValueError("At least one dataset_id is required")

    modalities = _modalities(records)
    route = route_workflow(
        WorkflowRequest.from_modalities(
            list(modalities),
            pairing_verified=pairing_verified,
            pairing_level=pairing_level,
        )
    )
    qc_gates, artifacts = _contract_for_route(route.route)
    return WorkflowPlan(
        route=route,
        dataset_ids=tuple(record.dataset_id for record in records),
        dataset_names=tuple(record.name for record in records),
        modalities=modalities,
        qc_gates=qc_gates,
        expected_artifacts=artifacts,
        trace_requirements=_trace_requirements(route.route),
        downloads_blocked=True,
        notes=_notes(records, route),
    )


def _modalities(records: tuple[DatasetRecord, ...]) -> tuple[str, ...]:
    ordered = []
    for candidate in ("PET", "MR", "CT", "WSI"):
        if any(candidate in record.modalities for record in records):
            ordered.append(candidate)
    return tuple(ordered)


def _contract_for_route(route: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    contracts = {
        "pet_mr_mainline": (
            (
                "pet_presence",
                "mr_presence",
                "subject_session_alignment",
                "preprocessing_compatibility",
                "label_availability",
                "trace_completeness",
            ),
            (
                "adni_case_selection_manifest",
                "oasis3_validation_manifest",
                "pet_only_baseline_report",
                "mr_only_baseline_report",
                "pet_mr_fusion_report",
                "qc_exclusion_report",
                "agent_trace_bundle",
            ),
        ),
        "pet_only_baseline": (
            ("pet_presence", "label_availability", "trace_completeness"),
            ("pet_only_baseline_report", "qc_exclusion_report", "agent_trace_bundle"),
        ),
        "mr_only_baseline": (
            ("mr_presence", "label_availability", "trace_completeness"),
            ("mr_only_baseline_report", "qc_exclusion_report", "agent_trace_bundle"),
        ),
        "wsi_preprocessing": (
            (
                "slide_readable",
                "tissue_detection",
                "artifact_filtering",
                "patch_extraction",
                "embedding_extraction",
                "trace_completeness",
            ),
            (
                "wsi_slide_inventory",
                "tissue_mask_manifest",
                "patch_manifest",
                "wsi_embedding_manifest",
                "wsi_qc_report",
                "agent_trace_bundle",
            ),
        ),
        "ct_branch": (
            (
                "ct_series_readable",
                "ct_metadata_sufficient",
                "annotation_availability",
                "baseline_output_generated",
                "trace_completeness",
            ),
            (
                "ct_collection_inventory",
                "ct_feature_manifest",
                "ct_qc_report",
                "ct_baseline_report",
                "agent_trace_bundle",
            ),
        ),
        "ct_wsi_separate_with_pairing_audit": (
            (
                "ct_series_readable",
                "slide_readable",
                "pairing_evidence_collected",
                "pairing_gate_evaluated",
                "trace_completeness",
            ),
            (
                "ct_collection_inventory",
                "wsi_slide_inventory",
                "pairing_audit_report",
                "ct_branch_report",
                "wsi_preprocessing_report",
                "agent_trace_bundle",
            ),
        ),
        "ct_pathology_fusion": (
            (
                "ct_series_readable",
                "slide_readable",
                "pairing_gate_passed",
                "missing_modality_reported",
                "trace_completeness",
            ),
            (
                "ct_collection_inventory",
                "wsi_slide_inventory",
                "pairing_audit_report",
                "ct_only_baseline_report",
                "wsi_only_baseline_report",
                "ct_wsi_fusion_report",
                "agent_trace_bundle",
            ),
        ),
    }
    return contracts.get(
        route,
        (
            ("dataset_availability_checked",),
            ("routing_report",),
        ),
    )


def _trace_requirements(route: str) -> tuple[str, ...]:
    base = (
        "input_modalities",
        "model_or_baseline",
        "parameters",
        "qc_result",
        "failure_state",
        "human_review_state",
        "evidence_source_records",
    )
    if route == "pet_mr_mainline":
        return base + ("main_conclusion_support_guard",)
    if route == "ct_pathology_fusion":
        return base + ("pairing_gate_status", "pairing_level")
    return base


def _notes(records: tuple[DatasetRecord, ...], route: WorkflowRoute) -> tuple[str, ...]:
    notes = [
        "Dataset downloads are blocked in this implementation phase; only source links and access status are used.",
        f"Route claim level: {route.claim_level}.",
    ]
    for record in records:
        if record.access_status != "downloaded":
            notes.append(f"{record.dataset_id}: access_status={record.access_status}.")
        notes.append(f"{record.dataset_id}: pairing_status={record.pairing_status}.")
    return tuple(notes)

