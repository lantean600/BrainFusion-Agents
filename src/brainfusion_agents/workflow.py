from __future__ import annotations

from dataclasses import dataclass, field


SUPPORTED_MODALITIES = {"PET", "MR", "CT", "WSI"}


@dataclass(frozen=True)
class WorkflowRequest:
    """Observable workflow routing inputs for available modalities."""

    modalities: frozenset[str]
    pairing_verified: bool = False
    pairing_level: str = "none"

    @classmethod
    def from_modalities(
        cls,
        modalities: list[str] | tuple[str, ...] | set[str],
        *,
        pairing_verified: bool = False,
        pairing_level: str = "none",
    ) -> "WorkflowRequest":
        normalized = frozenset(modality.upper() for modality in modalities)
        unsupported = normalized - SUPPORTED_MODALITIES
        if unsupported:
            raise ValueError(f"Unsupported modalities: {', '.join(sorted(unsupported))}")
        return cls(
            modalities=normalized,
            pairing_verified=pairing_verified,
            pairing_level=pairing_level,
        )


@dataclass(frozen=True)
class WorkflowRoute:
    route: str
    claim_level: str
    required_agents: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)


def route_workflow(request: WorkflowRequest) -> WorkflowRoute:
    """Return the primary route for a modality availability request."""

    modalities = request.modalities

    if {"PET", "MR"}.issubset(modalities):
        return WorkflowRoute(
            route="pet_mr_mainline",
            claim_level="main-conclusion-eligible",
            required_agents=(
                "Dataset Registry Agent",
                "Central Dispatcher Agent",
                "PET Agent",
                "MR Agent",
                "PET/MR Fusion Agent",
                "Evidence Agent",
            ),
            reasons=("PET and MR are available for the MVP mainline.",),
        )

    if modalities == {"PET"}:
        return WorkflowRoute(
            route="pet_only_baseline",
            claim_level="baseline-evidence-only",
            required_agents=("Dataset Registry Agent", "PET Agent", "Evidence Agent"),
            reasons=("PET is available without MR.",),
        )

    if modalities == {"MR"}:
        return WorkflowRoute(
            route="mr_only_baseline",
            claim_level="baseline-evidence-only",
            required_agents=("Dataset Registry Agent", "MR Agent", "Evidence Agent"),
            reasons=("MR is available without PET.",),
        )

    if {"CT", "WSI"}.issubset(modalities):
        if request.pairing_verified and request.pairing_level in {
            "patient-level",
            "lesion-level",
        }:
            return WorkflowRoute(
                route="ct_pathology_fusion",
                claim_level="formal-extension-eligible",
                required_agents=(
                    "Dataset Registry Agent",
                    "CT Agent",
                    "WSI Agent",
                    "Pairing Gate Agent",
                    "Evidence Agent",
                ),
                reasons=(f"CT and WSI pairing passed at {request.pairing_level}.",),
            )
        return WorkflowRoute(
            route="ct_wsi_separate_with_pairing_audit",
            claim_level="no-fusion-claim",
            required_agents=(
                "Dataset Registry Agent",
                "CT Agent",
                "WSI Agent",
                "Pairing Gate Agent",
                "Evidence Agent",
            ),
            reasons=("CT and WSI are available but pairing is not verified.",),
        )

    if modalities == {"WSI"}:
        return WorkflowRoute(
            route="wsi_preprocessing",
            claim_level="extension-preprocessing-evidence",
            required_agents=("Dataset Registry Agent", "WSI Agent", "Evidence Agent"),
            reasons=("WSI is available as a preprocessing branch.",),
        )

    if modalities == {"CT"}:
        return WorkflowRoute(
            route="ct_branch",
            claim_level="extension-prototype-evidence",
            required_agents=("Dataset Registry Agent", "CT Agent", "Evidence Agent"),
            reasons=("CT is available as a prototype branch.",),
        )

    return WorkflowRoute(
        route="unroutable",
        claim_level="no-claim",
        required_agents=("Dataset Registry Agent",),
        reasons=("No supported modality route is available.",),
    )


def plan_workflows(request: WorkflowRequest) -> tuple[WorkflowRoute, ...]:
    """Return workflow routes implied by all available modalities.

    The first route is the primary route. Additional routes are branch work that can
    proceed independently without weakening the PET/MR mainline.
    """

    primary = route_workflow(request)
    routes = [primary]

    if {"PET", "MR"}.issubset(request.modalities):
        remaining = request.modalities - {"PET", "MR"}
        if remaining:
            branch_request = WorkflowRequest(
                modalities=frozenset(remaining),
                pairing_verified=request.pairing_verified,
                pairing_level=request.pairing_level,
            )
            branch = route_workflow(branch_request)
            if branch.route != "unroutable":
                routes.append(branch)

    return tuple(routes)

