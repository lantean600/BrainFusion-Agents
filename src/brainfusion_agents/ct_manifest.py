from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import ManifestFinding, ManifestValidationResult


REQUIRED_CT_RECORD_FIELDS = (
    "case_id",
    "study_id",
    "series_id",
    "source_record",
    "ct_protocol",
    "ct_series_readable",
    "metadata_sufficient",
    "annotation_available",
    "lesion_reference",
    "baseline_type",
    "baseline_status",
    "feature_manifest_status",
    "qc_status",
    "trace_id",
)

ALLOWED_BASELINE_TYPES = {"segmentation", "classification", "radiomics", "feature-extraction"}
ALLOWED_CT_STATUSES = {"planned", "pass", "warn", "fail", "skipped", "needs-human-review"}
FORBIDDEN_CT_PATH_FIELDS = {
    "local_path",
    "download_path",
    "dicom_path",
    "ct_path",
    "series_path",
    "annotation_path",
    "feature_path",
}


def ct_manifest_template() -> dict[str, Any]:
    return {
        "manifest_type": "ct_prototype",
        "dataset_id": "lidc-idri",
        "description": "CT prototype manifest template. Keep source identifiers and planned CT baseline state only; do not add local DICOM or image paths.",
        "required_record_fields": list(REQUIRED_CT_RECORD_FIELDS),
        "records": [],
    }


def validate_ct_manifest(
    manifest: dict[str, Any] | str | Path,
) -> ManifestValidationResult:
    payload = _load_manifest(manifest)
    errors: list[ManifestFinding] = []
    warnings: list[ManifestFinding] = []

    manifest_type = str(payload.get("manifest_type", ""))
    dataset_id = payload.get("dataset_id")
    records = payload.get("records", [])

    if manifest_type != "ct_prototype":
        errors.append(
            ManifestFinding("error", None, "manifest_type", "Manifest type must be ct_prototype.")
        )
    if not dataset_id:
        errors.append(ManifestFinding("error", None, "dataset_id", "dataset_id is required."))
    if not isinstance(records, list):
        errors.append(ManifestFinding("error", None, "records", "records must be a list."))
        records = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(ManifestFinding("error", index, "record", "record must be an object."))
            continue
        _validate_ct_record(index, record, errors, warnings)

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


def _validate_ct_record(
    index: int,
    record: dict[str, Any],
    errors: list[ManifestFinding],
    warnings: list[ManifestFinding],
) -> None:
    for field in REQUIRED_CT_RECORD_FIELDS:
        if field not in record:
            errors.append(ManifestFinding("error", index, field, f"{field} is required."))

    for field in FORBIDDEN_CT_PATH_FIELDS:
        if field in record:
            errors.append(
                ManifestFinding(
                    "error",
                    index,
                    field,
                    f"{field} is forbidden in no-download CT manifests; keep source identifiers only.",
                )
            )

    for field in ("case_id", "study_id", "series_id", "source_record", "ct_protocol", "trace_id"):
        if field in record and not str(record[field]).strip():
            errors.append(ManifestFinding("error", index, field, f"{field} must not be empty."))

    for field in ("ct_series_readable", "metadata_sufficient", "annotation_available"):
        if field in record and not isinstance(record[field], bool):
            errors.append(ManifestFinding("error", index, field, f"{field} must be boolean."))

    if record.get("ct_series_readable") is not True:
        errors.append(
            ManifestFinding(
                "error",
                index,
                "ct_series_readable",
                "ct_series_readable must be true for CT prototype readiness.",
            )
        )
    if record.get("metadata_sufficient") is not True:
        errors.append(
            ManifestFinding(
                "error",
                index,
                "metadata_sufficient",
                "metadata_sufficient must be true for CT prototype readiness.",
            )
        )

    if "baseline_type" in record and record["baseline_type"] not in ALLOWED_BASELINE_TYPES:
        errors.append(ManifestFinding("error", index, "baseline_type", "Invalid baseline_type."))

    for field in ("baseline_status", "feature_manifest_status", "qc_status"):
        if field in record and record[field] not in ALLOWED_CT_STATUSES:
            errors.append(ManifestFinding("error", index, field, f"Invalid {field}."))
        if field in record and record[field] in {"warn", "needs-human-review"}:
            warnings.append(
                ManifestFinding("warning", index, field, f"{field} requires review.")
            )

