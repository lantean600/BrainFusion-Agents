from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import ManifestFinding
from .pairing import PairingEvidence, evaluate_pairing_gate


FORBIDDEN_PAIRING_PATH_FIELDS = {
    "local_path",
    "download_path",
    "ct_path",
    "wsi_path",
    "pairing_file_path",
}


@dataclass(frozen=True)
class PairingManifestValidationResult:
    passed: bool
    manifest_type: str
    gate_status: str
    pairing_level: str
    paired_patient_count: int
    paired_lesion_count: int | None
    errors: tuple[ManifestFinding, ...]
    warnings: tuple[ManifestFinding, ...]
    limitations: tuple[str, ...]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "manifest_type": self.manifest_type,
            "gate_status": self.gate_status,
            "pairing_level": self.pairing_level,
            "paired_patient_count": self.paired_patient_count,
            "paired_lesion_count": self.paired_lesion_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [finding.__dict__ for finding in self.errors],
            "warnings": [finding.__dict__ for finding in self.warnings],
            "limitations": list(self.limitations),
        }


def pairing_manifest_template() -> dict[str, Any]:
    return {
        "manifest_type": "ct_pathology_pairing_audit",
        "description": "CT-pathology pairing audit template. Keep source identifiers and audit evidence only; do not add local data paths.",
        "source_datasets": ["tcia", "tcga-gdc"],
        "identifier_fields": [],
        "paired_patient_count": 0,
        "paired_lesion_count": None,
        "timing_assumption": "",
        "endpoint_available": False,
        "evidence": [],
    }


def validate_pairing_manifest(
    manifest: dict[str, Any] | str | Path,
) -> PairingManifestValidationResult:
    payload = _load_manifest(manifest)
    errors: list[ManifestFinding] = []
    warnings: list[ManifestFinding] = []

    manifest_type = str(payload.get("manifest_type", ""))
    if manifest_type != "ct_pathology_pairing_audit":
        errors.append(
            ManifestFinding(
                "error",
                None,
                "manifest_type",
                "Manifest type must be ct_pathology_pairing_audit.",
            )
        )

    for field in FORBIDDEN_PAIRING_PATH_FIELDS:
        if field in payload:
            errors.append(
                ManifestFinding(
                    "error",
                    None,
                    field,
                    f"{field} is forbidden in no-download pairing manifests; keep source identifiers only.",
                )
            )

    source_datasets = _string_tuple(payload.get("source_datasets", []))
    identifier_fields = _string_tuple(payload.get("identifier_fields", []))
    paired_patient_count = _int_value(payload.get("paired_patient_count", 0))
    paired_lesion_count = _optional_int_value(payload.get("paired_lesion_count"))
    timing_assumption = str(payload.get("timing_assumption") or "")
    endpoint_available = payload.get("endpoint_available", False)
    evidence = payload.get("evidence", [])

    if len(source_datasets) < 2:
        errors.append(
            ManifestFinding(
                "error",
                None,
                "source_datasets",
                "source_datasets must include at least two datasets.",
            )
        )
    if not identifier_fields:
        errors.append(
            ManifestFinding(
                "error",
                None,
                "identifier_fields",
                "identifier_fields are required for pairing audit.",
            )
        )
    if paired_patient_count < 0:
        errors.append(
            ManifestFinding(
                "error",
                None,
                "paired_patient_count",
                "paired_patient_count must be non-negative.",
            )
        )
    if paired_lesion_count is not None and paired_lesion_count < 0:
        errors.append(
            ManifestFinding(
                "error",
                None,
                "paired_lesion_count",
                "paired_lesion_count must be non-negative.",
            )
        )
    if not isinstance(endpoint_available, bool):
        errors.append(
            ManifestFinding(
                "error",
                None,
                "endpoint_available",
                "endpoint_available must be boolean.",
            )
        )
        endpoint_available = False
    if not isinstance(evidence, list):
        errors.append(
            ManifestFinding("error", None, "evidence", "evidence must be a list.")
        )
        evidence = []
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            errors.append(
                ManifestFinding("error", index, "evidence", "evidence item must be an object.")
            )
            continue
        for field in FORBIDDEN_PAIRING_PATH_FIELDS:
            if field in record:
                errors.append(
                    ManifestFinding(
                        "error",
                        index,
                        field,
                        f"{field} is forbidden in no-download pairing evidence.",
                    )
                )

    gate = evaluate_pairing_gate(
        PairingEvidence(
            source_datasets=source_datasets,
            identifier_fields=identifier_fields,
            paired_patient_count=paired_patient_count,
            paired_lesion_count=paired_lesion_count,
            timing_assumption=timing_assumption or None,
            endpoint_available=bool(endpoint_available),
        )
    )
    for limitation in gate.limitations:
        errors.append(ManifestFinding("error", None, "pairing_gate", limitation))

    return PairingManifestValidationResult(
        passed=not errors and gate.passed,
        manifest_type=manifest_type,
        gate_status=gate.status,
        pairing_level=gate.pairing_level,
        paired_patient_count=gate.paired_patient_count,
        paired_lesion_count=gate.paired_lesion_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
        limitations=gate.limitations,
    )


def _load_manifest(manifest: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(manifest, dict):
        return manifest
    return json.loads(Path(manifest).read_text(encoding="utf-8"))


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _int_value(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def _optional_int_value(value: Any) -> int | None:
    if value is None:
        return None
    return _int_value(value)

