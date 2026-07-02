from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_RECORD_FIELDS = (
    "subject_id",
    "session_id",
    "diagnosis_label",
    "clinical_timepoint",
    "pet_available",
    "mr_available",
    "pet_tracer",
    "mr_sequence",
    "pet_qc_status",
    "mr_qc_status",
    "alignment_status",
    "source_record",
)

ALLOWED_QC_STATUSES = {"pass", "warn", "fail", "needs-human-review"}
ALLOWED_ALIGNMENT_STATUSES = {
    "subject-session",
    "nearest-clinical-visit",
    "missing-pet",
    "missing-mr",
    "unverified",
}
FORBIDDEN_PATH_FIELDS = {"local_path", "download_path", "pet_path", "mr_path"}


@dataclass(frozen=True)
class ManifestFinding:
    severity: str
    record_index: int | None
    field: str
    message: str


@dataclass(frozen=True)
class ManifestValidationResult:
    passed: bool
    manifest_type: str
    dataset_id: str | None
    record_count: int
    errors: tuple[ManifestFinding, ...]
    warnings: tuple[ManifestFinding, ...]

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
            "dataset_id": self.dataset_id,
            "record_count": self.record_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [finding.__dict__ for finding in self.errors],
            "warnings": [finding.__dict__ for finding in self.warnings],
        }


def case_selection_manifest_template() -> dict[str, Any]:
    return {
        "manifest_type": "pet_mr_case_selection",
        "dataset_id": "adni",
        "description": "PET/MR case selection manifest template. Keep source identifiers only; do not add local image paths.",
        "required_record_fields": list(REQUIRED_RECORD_FIELDS),
        "records": [],
    }


def validate_case_selection_manifest(
    manifest: dict[str, Any] | str | Path,
) -> ManifestValidationResult:
    payload = _load_manifest(manifest)
    errors: list[ManifestFinding] = []
    warnings: list[ManifestFinding] = []

    manifest_type = str(payload.get("manifest_type", ""))
    dataset_id = payload.get("dataset_id")
    records = payload.get("records", [])

    if manifest_type != "pet_mr_case_selection":
        errors.append(
            ManifestFinding(
                "error",
                None,
                "manifest_type",
                "Manifest type must be pet_mr_case_selection.",
            )
        )
    if not dataset_id:
        errors.append(
            ManifestFinding("error", None, "dataset_id", "dataset_id is required.")
        )
    if not isinstance(records, list):
        errors.append(
            ManifestFinding("error", None, "records", "records must be a list.")
        )
        records = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(
                ManifestFinding("error", index, "record", "record must be an object.")
            )
            continue
        _validate_record(index, record, errors, warnings)

    return ManifestValidationResult(
        passed=not errors,
        manifest_type=manifest_type,
        dataset_id=str(dataset_id) if dataset_id is not None else None,
        record_count=len(records),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _load_manifest(manifest: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(manifest, dict):
        return manifest
    return json.loads(Path(manifest).read_text(encoding="utf-8"))


def _validate_record(
    index: int,
    record: dict[str, Any],
    errors: list[ManifestFinding],
    warnings: list[ManifestFinding],
) -> None:
    for field in REQUIRED_RECORD_FIELDS:
        if field not in record:
            errors.append(
                ManifestFinding("error", index, field, f"{field} is required.")
            )

    for field in FORBIDDEN_PATH_FIELDS:
        if field in record:
            errors.append(
                ManifestFinding(
                    "error",
                    index,
                    field,
                    f"{field} is forbidden in no-download manifests; keep source identifiers only.",
                )
            )

    for field in ("subject_id", "session_id", "diagnosis_label", "clinical_timepoint", "source_record"):
        if field in record and not str(record[field]).strip():
            errors.append(
                ManifestFinding("error", index, field, f"{field} must not be empty.")
            )

    for field in ("pet_available", "mr_available"):
        if field in record and not isinstance(record[field], bool):
            errors.append(
                ManifestFinding("error", index, field, f"{field} must be boolean.")
            )

    if record.get("pet_available") is not True:
        errors.append(
            ManifestFinding(
                "error",
                index,
                "pet_available",
                "pet_available must be true for PET/MR mainline case selection.",
            )
        )
    if record.get("mr_available") is not True:
        errors.append(
            ManifestFinding(
                "error",
                index,
                "mr_available",
                "mr_available must be true for PET/MR mainline case selection.",
            )
        )

    if "pet_qc_status" in record and record["pet_qc_status"] not in ALLOWED_QC_STATUSES:
        errors.append(
            ManifestFinding("error", index, "pet_qc_status", "Invalid pet_qc_status.")
        )
    if "mr_qc_status" in record and record["mr_qc_status"] not in ALLOWED_QC_STATUSES:
        errors.append(
            ManifestFinding("error", index, "mr_qc_status", "Invalid mr_qc_status.")
        )
    if (
        "alignment_status" in record
        and record["alignment_status"] not in ALLOWED_ALIGNMENT_STATUSES
    ):
        errors.append(
            ManifestFinding(
                "error",
                index,
                "alignment_status",
                "Invalid alignment_status.",
            )
        )

    if record.get("pet_qc_status") in {"warn", "needs-human-review"}:
        warnings.append(
            ManifestFinding("warning", index, "pet_qc_status", "PET QC requires review.")
        )
    if record.get("mr_qc_status") in {"warn", "needs-human-review"}:
        warnings.append(
            ManifestFinding("warning", index, "mr_qc_status", "MR QC requires review.")
        )

