from __future__ import annotations

from dataclasses import dataclass

from .datasets import DatasetRegistry


ALLOWED_PAIRING_STATUSES = {
    "subject-session-alignment-required",
    "not-a-pet-mr-main-dataset",
    "ct-only",
    "candidate-pairing-review",
    "wsi-branch-pairing-audit-required",
    "benchmark-only",
    "unverified",
}


@dataclass(frozen=True)
class RegistryAuditFinding:
    severity: str
    dataset_id: str
    message: str


@dataclass(frozen=True)
class RegistryAuditResult:
    passed: bool
    dataset_ids: tuple[str, ...]
    errors: tuple[RegistryAuditFinding, ...]
    warnings: tuple[RegistryAuditFinding, ...]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "dataset_ids": list(self.dataset_ids),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [finding.__dict__ for finding in self.errors],
            "warnings": [finding.__dict__ for finding in self.warnings],
        }


def audit_dataset_registry(registry: DatasetRegistry) -> RegistryAuditResult:
    records = registry.list()
    errors: list[RegistryAuditFinding] = []
    warnings: list[RegistryAuditFinding] = []

    dataset_ids = tuple(record.dataset_id for record in records)
    roles = {record.dataset_id: record.role for record in records}

    _require_dataset("adni", dataset_ids, errors)
    _require_dataset("oasis-3", dataset_ids, errors)
    if roles.get("adni") != "primary-development":
        errors.append(
            RegistryAuditFinding("error", "adni", "ADNI must be the primary-development dataset.")
        )
    if roles.get("oasis-3") != "external-validation":
        errors.append(
            RegistryAuditFinding("error", "oasis-3", "OASIS-3 must be the external-validation dataset.")
        )

    for record in records:
        if record.access_status == "downloaded":
            errors.append(
                RegistryAuditFinding(
                    "error",
                    record.dataset_id,
                    "Dataset access_status must not be downloaded in the current no-download phase.",
                )
            )
        if not record.source_urls:
            errors.append(
                RegistryAuditFinding(
                    "error",
                    record.dataset_id,
                    "Dataset must keep at least one source URL.",
                )
            )
        for url in record.source_urls:
            if not url.startswith(("https://", "http://")):
                errors.append(
                    RegistryAuditFinding(
                        "error",
                        record.dataset_id,
                        f"Source URL must be an HTTP(S) link: {url}",
                    )
                )
        if record.pairing_status not in ALLOWED_PAIRING_STATUSES:
            errors.append(
                RegistryAuditFinding(
                    "error",
                    record.dataset_id,
                    f"Unexpected pairing_status: {record.pairing_status}",
                )
            )

        modalities = set(record.modalities)
        if {"CT", "WSI"}.issubset(modalities) and record.pairing_status != "unverified":
            errors.append(
                RegistryAuditFinding(
                    "error",
                    record.dataset_id,
                    "CT+WSI candidate datasets must remain unverified until pairing gate evidence is recorded.",
                )
            )
        if record.branch == "pet-mr-mainline" and modalities != {"PET", "MR"}:
            errors.append(
                RegistryAuditFinding(
                    "error",
                    record.dataset_id,
                    "PET/MR mainline datasets must declare exactly PET and MR modalities.",
                )
            )
        if record.branch == "ct-pathology-extension" and "unverified" not in record.pairing_status:
            warnings.append(
                RegistryAuditFinding(
                    "warning",
                    record.dataset_id,
                    "CT-pathology extension entries should remain unverified until a pairing audit is materialized.",
                )
            )

    return RegistryAuditResult(
        passed=not errors,
        dataset_ids=dataset_ids,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _require_dataset(
    dataset_id: str,
    dataset_ids: tuple[str, ...],
    errors: list[RegistryAuditFinding],
) -> None:
    if dataset_id not in dataset_ids:
        errors.append(
            RegistryAuditFinding(
                "error",
                dataset_id,
                f"Required dataset is missing from registry: {dataset_id}",
            )
        )

