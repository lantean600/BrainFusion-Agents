from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


QC_STATUSES = {"pass", "warn", "fail", "needs-human-review"}
FAILURE_CATEGORIES = {
    "data-missing",
    "qc-failed",
    "model-error",
    "pairing-unverified",
    "access-blocked",
    "none",
}


@dataclass(frozen=True)
class QCResult:
    status: str
    checks: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FailureState:
    failed: bool
    category: str = "none"
    message: str | None = None


@dataclass(frozen=True)
class HumanReviewState:
    required: bool = False
    completed: bool = False
    reviewer: str | None = None


@dataclass(frozen=True)
class EvidenceBundle:
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    metrics: dict[str, Any] = field(default_factory=dict)
    source_records: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConclusionSupport:
    supports_main_conclusion: bool = False
    supports_extension_experiment: bool = False
    limitations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AgentTrace:
    trace_id: str
    workflow_id: str
    agent_name: str
    agent_version: str
    dataset_id: str
    subject_id: str
    session_id: str | None
    input_modalities: tuple[str, ...]
    task: str
    model_name: str | None
    model_version: str | None
    parameters: dict[str, Any]
    qc: QCResult
    failure: FailureState
    human_review: HumanReviewState
    evidence: EvidenceBundle
    conclusion_support: ConclusionSupport
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "workflow_id": self.workflow_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "dataset_id": self.dataset_id,
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "input_modalities": list(self.input_modalities),
            "task": self.task,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "parameters": self.parameters,
            "qc": {
                "status": self.qc.status,
                "checks": list(self.qc.checks),
                "reasons": list(self.qc.reasons),
            },
            "failure": {
                "failed": self.failure.failed,
                "category": self.failure.category,
                "message": self.failure.message,
            },
            "human_review": {
                "required": self.human_review.required,
                "completed": self.human_review.completed,
                "reviewer": self.human_review.reviewer,
            },
            "evidence": {
                "artifacts": list(self.evidence.artifacts),
                "metrics": self.evidence.metrics,
                "source_records": list(self.evidence.source_records),
            },
            "conclusion_support": {
                "supports_main_conclusion": self.conclusion_support.supports_main_conclusion,
                "supports_extension_experiment": self.conclusion_support.supports_extension_experiment,
                "limitations": list(self.conclusion_support.limitations),
            },
            "created_at": self.created_at,
        }


def validate_trace(trace: AgentTrace) -> tuple[str, ...]:
    errors: list[str] = []

    if trace.qc.status not in QC_STATUSES:
        errors.append(f"Invalid QC status: {trace.qc.status}")

    if trace.failure.category not in FAILURE_CATEGORIES:
        errors.append(f"Invalid failure category: {trace.failure.category}")

    if trace.failure.failed and trace.failure.category == "none":
        errors.append("Failed traces must use a non-none failure category.")

    if not trace.failure.failed and trace.failure.category != "none":
        errors.append("Non-failed traces must use failure category 'none'.")

    supports_any_conclusion = (
        trace.conclusion_support.supports_main_conclusion
        or trace.conclusion_support.supports_extension_experiment
    )

    if supports_any_conclusion and trace.human_review.required and not trace.human_review.completed:
        errors.append("Trace cannot support a conclusion while required human review is incomplete.")

    if supports_any_conclusion and not trace.evidence.source_records:
        errors.append("Conclusion-supporting traces must include source records.")

    if trace.conclusion_support.supports_main_conclusion:
        if trace.workflow_id != "pet_mr_mainline":
            errors.append("Only PET/MR mainline traces can support the main conclusion.")
        if set(trace.input_modalities) != {"PET", "MR"}:
            errors.append("Main conclusion traces must include PET and MR input modalities.")
        if trace.qc.status != "pass":
            errors.append("Main conclusion traces require QC status 'pass'.")
        if trace.failure.failed:
            errors.append("Failed traces cannot support the main conclusion.")

    if (
        trace.conclusion_support.supports_extension_experiment
        and trace.workflow_id == "ct_pathology_fusion"
    ):
        if trace.parameters.get("pairing_gate_status") != "pass":
            errors.append("CT-pathology extension traces require a passed pairing gate.")
        if trace.parameters.get("pairing_level") not in {"patient-level", "lesion-level"}:
            errors.append("CT-pathology extension traces require patient-level or lesion-level pairing.")

    return tuple(errors)

