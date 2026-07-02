from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PairingEvidence:
    source_datasets: tuple[str, ...]
    identifier_fields: tuple[str, ...]
    paired_patient_count: int = 0
    paired_lesion_count: int | None = None
    timing_assumption: str | None = None
    endpoint_available: bool = False
    notes: str = ""


@dataclass(frozen=True)
class PairingGateResult:
    status: str
    pairing_level: str
    paired_patient_count: int
    paired_lesion_count: int | None
    source_datasets: tuple[str, ...]
    evidence_records: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def evaluate_pairing_gate(evidence: PairingEvidence) -> PairingGateResult:
    limitations: list[str] = []
    evidence_records: list[str] = []

    if len(evidence.source_datasets) < 2:
        limitations.append("At least two source datasets are required for CT-pathology pairing.")
    else:
        evidence_records.append(
            "source_datasets=" + ",".join(sorted(evidence.source_datasets))
        )

    if not evidence.identifier_fields:
        limitations.append("Identifier fields used for matching are missing.")
    else:
        evidence_records.append(
            "identifier_fields=" + ",".join(sorted(evidence.identifier_fields))
        )

    if evidence.paired_patient_count <= 0:
        limitations.append("No patient-level paired records were verified.")

    if evidence.paired_lesion_count is not None and evidence.paired_lesion_count > 0:
        pairing_level = "lesion-level"
    elif evidence.paired_patient_count > 0:
        pairing_level = "patient-level"
    else:
        pairing_level = "none"

    if not evidence.timing_assumption:
        limitations.append("Imaging/pathology timing assumption is not recorded.")
    else:
        evidence_records.append(f"timing_assumption={evidence.timing_assumption}")

    if not evidence.endpoint_available:
        limitations.append("Clinical endpoint availability is not confirmed.")

    status = "pass" if pairing_level in {"patient-level", "lesion-level"} and not limitations else "fail"

    return PairingGateResult(
        status=status,
        pairing_level=pairing_level,
        paired_patient_count=evidence.paired_patient_count,
        paired_lesion_count=evidence.paired_lesion_count,
        source_datasets=evidence.source_datasets,
        evidence_records=tuple(evidence_records),
        limitations=tuple(limitations),
    )

