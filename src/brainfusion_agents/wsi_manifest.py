from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import ManifestFinding, ManifestValidationResult


REQUIRED_WSI_RECORD_FIELDS = (
    "case_id",
    "slide_id",
    "source_record",
    "magnification",
    "resolution",
    "slide_readable",
    "tissue_detection_status",
    "artifact_filtering_status",
    "stain_normalization_status",
    "patch_extraction_status",
    "embedding_status",
    "patch_count",
    "embedding_model",
    "qc_status",
    "trace_id",
)

ALLOWED_WSI_STATUSES = {"planned", "pass", "warn", "fail", "skipped", "needs-human-review"}
FORBIDDEN_WSI_PATH_FIELDS = {
    "local_path",
    "download_path",
    "slide_path",
    "wsi_path",
    "patch_path",
    "embedding_path",
}


def wsi_manifest_template() -> dict[str, Any]:
    return {
        "manifest_type": "wsi_preprocessing",
        "dataset_id": "tcga-gdc-wsi",
        "description": "WSI preprocessing manifest template. Keep source identifiers and planned preprocessing state only; do not add local slide paths.",
        "required_record_fields": list(REQUIRED_WSI_RECORD_FIELDS),
        "records": [],
    }


def validate_wsi_manifest(
    manifest: dict[str, Any] | str | Path,
) -> ManifestValidationResult:
    payload = _load_manifest(manifest)
    errors: list[ManifestFinding] = []
    warnings: list[ManifestFinding] = []

    manifest_type = str(payload.get("manifest_type", ""))
    dataset_id = payload.get("dataset_id")
    records = payload.get("records", [])

    if manifest_type != "wsi_preprocessing":
        errors.append(
            ManifestFinding(
                "error",
                None,
                "manifest_type",
                "Manifest type must be wsi_preprocessing.",
            )
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
        _validate_wsi_record(index, record, errors, warnings)

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


def _validate_wsi_record(
    index: int,
    record: dict[str, Any],
    errors: list[ManifestFinding],
    warnings: list[ManifestFinding],
) -> None:
    for field in REQUIRED_WSI_RECORD_FIELDS:
        if field not in record:
            errors.append(ManifestFinding("error", index, field, f"{field} is required."))

    for field in FORBIDDEN_WSI_PATH_FIELDS:
        if field in record:
            errors.append(
                ManifestFinding(
                    "error",
                    index,
                    field,
                    f"{field} is forbidden in no-download WSI manifests; keep source identifiers only.",
                )
            )

    for field in ("case_id", "slide_id", "source_record", "magnification", "resolution", "trace_id"):
        if field in record and not str(record[field]).strip():
            errors.append(ManifestFinding("error", index, field, f"{field} must not be empty."))

    if "slide_readable" in record and not isinstance(record["slide_readable"], bool):
        errors.append(
            ManifestFinding("error", index, "slide_readable", "slide_readable must be boolean.")
        )
    if record.get("slide_readable") is not True:
        errors.append(
            ManifestFinding(
                "error",
                index,
                "slide_readable",
                "slide_readable must be true for WSI preprocessing readiness.",
            )
        )

    for field in (
        "tissue_detection_status",
        "artifact_filtering_status",
        "stain_normalization_status",
        "patch_extraction_status",
        "embedding_status",
        "qc_status",
    ):
        if field in record and record[field] not in ALLOWED_WSI_STATUSES:
            errors.append(ManifestFinding("error", index, field, f"Invalid {field}."))
        if field in record and record[field] in {"warn", "needs-human-review"}:
            warnings.append(
                ManifestFinding("warning", index, field, f"{field} requires review.")
            )

    if "patch_count" in record:
        patch_count = record["patch_count"]
        if isinstance(patch_count, bool) or not isinstance(patch_count, int) or patch_count < 0:
            errors.append(
                ManifestFinding(
                    "error",
                    index,
                    "patch_count",
                    "patch_count must be a non-negative integer.",
                )
            )

