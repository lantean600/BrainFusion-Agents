from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .datasets import DatasetRegistry
from .plans import WorkflowPlan, build_workflow_plan
from .trace import (
    AgentTrace,
    ConclusionSupport,
    EvidenceBundle,
    FailureState,
    HumanReviewState,
    QCResult,
)


@dataclass(frozen=True)
class DryRunEvidenceBundle:
    workflow_id: str
    route_claim_level: str
    dataset_ids: tuple[str, ...]
    dataset_names: tuple[str, ...]
    planned_artifacts: tuple[str, ...]
    artifact_status: dict[str, str]
    traces: tuple[AgentTrace, ...]
    downloads_blocked: bool
    data_downloaded: bool
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "route_claim_level": self.route_claim_level,
            "dataset_ids": list(self.dataset_ids),
            "dataset_names": list(self.dataset_names),
            "planned_artifacts": list(self.planned_artifacts),
            "artifact_status": self.artifact_status,
            "traces": [trace.to_dict() for trace in self.traces],
            "downloads_blocked": self.downloads_blocked,
            "data_downloaded": self.data_downloaded,
            "limitations": list(self.limitations),
        }


def build_dry_run_evidence_bundle(
    registry: DatasetRegistry,
    dataset_ids: list[str] | tuple[str, ...],
    *,
    pairing_verified: bool = False,
    pairing_level: str = "none",
) -> DryRunEvidenceBundle:
    plan = build_workflow_plan(
        registry,
        dataset_ids,
        pairing_verified=pairing_verified,
        pairing_level=pairing_level,
    )
    limitations = _limitations(plan)
    traces = tuple(_trace_for_agent(plan, agent_name, limitations) for agent_name in plan.route.required_agents)

    return DryRunEvidenceBundle(
        workflow_id=plan.route.route,
        route_claim_level=plan.route.claim_level,
        dataset_ids=plan.dataset_ids,
        dataset_names=plan.dataset_names,
        planned_artifacts=plan.expected_artifacts,
        artifact_status={artifact: "planned" for artifact in plan.expected_artifacts},
        traces=traces,
        downloads_blocked=plan.downloads_blocked,
        data_downloaded=False,
        limitations=limitations,
    )


def _limitations(plan: WorkflowPlan) -> tuple[str, ...]:
    limitations = [
        "Dataset downloads are blocked in this implementation phase.",
        "Dry-run evidence cannot support main conclusions or extension experiment conclusions.",
    ]
    if plan.route.route == "ct_wsi_separate_with_pairing_audit":
        limitations.append("CT-pathology pairing is unverified; fusion artifacts are not planned.")
    limitations.extend(plan.notes)
    return tuple(dict.fromkeys(limitations))


def _trace_for_agent(
    plan: WorkflowPlan,
    agent_name: str,
    limitations: tuple[str, ...],
) -> AgentTrace:
    failure = _failure_for_agent(plan, agent_name)
    qc_status = "fail" if failure.category == "pairing-unverified" else "needs-human-review"
    return AgentTrace(
        trace_id=f"dry-run:{plan.route.route}:{_slug(agent_name)}",
        workflow_id=plan.route.route,
        agent_name=agent_name,
        agent_version="dry-run",
        dataset_id="+".join(plan.dataset_ids),
        subject_id="DRY-RUN",
        session_id=None,
        input_modalities=plan.modalities,
        task=f"dry_run_{plan.route.route}",
        model_name=None,
        model_version=None,
        parameters={
            "dry_run": True,
            "downloads_blocked": plan.downloads_blocked,
            "planned_qc_gates": list(plan.qc_gates),
            "planned_artifacts": list(plan.expected_artifacts),
            "pairing_gate_status": _pairing_gate_status(plan),
            "pairing_level": _pairing_level(plan),
        },
        qc=QCResult(
            status=qc_status,
            checks=plan.qc_gates,
            reasons=("Dry run only; no dataset files were inspected.",),
        ),
        failure=failure,
        human_review=HumanReviewState(required=True, completed=False),
        evidence=EvidenceBundle(
            artifacts=tuple(f"planned:{artifact}" for artifact in plan.expected_artifacts),
            metrics={},
            source_records=tuple(f"dataset:{dataset_id}" for dataset_id in plan.dataset_ids),
        ),
        conclusion_support=ConclusionSupport(
            supports_main_conclusion=False,
            supports_extension_experiment=False,
            limitations=limitations,
        ),
    )


def _failure_for_agent(plan: WorkflowPlan, agent_name: str) -> FailureState:
    if (
        plan.route.route == "ct_wsi_separate_with_pairing_audit"
        and agent_name == "Pairing Gate Agent"
    ):
        return FailureState(
            failed=True,
            category="pairing-unverified",
            message="CT-pathology fusion is blocked until patient-level or lesion-level pairing is verified.",
        )
    return FailureState(
        failed=True,
        category="access-blocked",
        message="Dry run does not download or inspect controlled dataset files.",
    )


def _pairing_gate_status(plan: WorkflowPlan) -> str:
    if plan.route.route == "ct_pathology_fusion":
        return "pass"
    if plan.route.route == "ct_wsi_separate_with_pairing_audit":
        return "fail"
    return "not-applicable"


def _pairing_level(plan: WorkflowPlan) -> str:
    if plan.route.route == "ct_pathology_fusion":
        for reason in plan.route.reasons:
            if "patient-level" in reason:
                return "patient-level"
            if "lesion-level" in reason:
                return "lesion-level"
    return "none"


def _slug(value: str) -> str:
    return value.lower().replace("/", "-").replace(" ", "-")

