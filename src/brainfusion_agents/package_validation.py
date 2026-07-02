from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FORBIDDEN_PACKAGE_TEXT = (
    "local_path",
    "download_path",
    "dicom_path",
    "slide_path",
    "patch_path",
    '"data_downloaded": true',
    '"downloads_blocked": false',
    '"supports_main_conclusion": true',
    '"supports_extension_experiment": true',
    '"publishable_main_conclusion_supported": true',
    '"extension_experiment_supported": true',
)


@dataclass(frozen=True)
class ProjectPackageValidationFinding:
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class ProjectPackageValidationResult:
    passed: bool
    package_root: str
    checked_file_count: int
    branch_count: int
    errors: tuple[ProjectPackageValidationFinding, ...]
    warnings: tuple[ProjectPackageValidationFinding, ...]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "package_root": self.package_root,
            "checked_file_count": self.checked_file_count,
            "branch_count": self.branch_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [finding.__dict__ for finding in self.errors],
            "warnings": [finding.__dict__ for finding in self.warnings],
        }


def validate_project_package(package_dir: str | Path) -> ProjectPackageValidationResult:
    root = Path(package_dir)
    errors: list[ProjectPackageValidationFinding] = []
    warnings: list[ProjectPackageValidationFinding] = []
    checked_files: set[Path] = set()

    if not root.exists():
        errors.append(_finding(root, "Package directory does not exist."))
        return _result(root, checked_files, 0, errors, warnings)
    if not root.is_dir():
        errors.append(_finding(root, "Package path is not a directory."))
        return _result(root, checked_files, 0, errors, warnings)

    manifest = _read_required_json(root / "manifest.json", root, checked_files, errors)
    status = _read_required_json(root / "project_status.json", root, checked_files, errors)
    if not manifest or not status:
        return _result(root, checked_files, 0, errors, warnings)

    _validate_root_manifest(manifest, root, errors)
    _validate_project_status(status, root, errors)

    branch_records = manifest.get("branches", [])
    if not isinstance(branch_records, list):
        errors.append(_finding(root / "manifest.json", "branches must be a list."))
        branch_records = []

    for relative_path in manifest.get("files", []):
        if not isinstance(relative_path, str):
            errors.append(_finding(root / "manifest.json", "files entries must be strings."))
            continue
        path = root / relative_path
        if not path.exists():
            errors.append(_finding(path, "File listed in root manifest does not exist."))

    for branch in branch_records:
        if not isinstance(branch, dict):
            errors.append(_finding(root / "manifest.json", "branch entries must be objects."))
            continue
        _validate_branch_package(branch, root, checked_files, errors)

    _scan_json_files(root, checked_files, errors)

    return _result(root, checked_files, len(branch_records), errors, warnings)


def _validate_root_manifest(
    manifest: dict[str, Any],
    root: Path,
    errors: list[ProjectPackageValidationFinding],
) -> None:
    checks = {
        "schema_version": "brainfusion-project-dry-run/v1",
        "release_stage": "metadata-dry-run",
        "cloud_runnable": True,
        "dry_run_only": True,
        "data_downloaded": False,
        "no_download_enforced": True,
        "publishable_main_conclusion_supported": False,
        "extension_experiment_supported": False,
    }
    for key, expected in checks.items():
        if manifest.get(key) != expected:
            errors.append(_finding(root / "manifest.json", f"{key} must be {expected!r}."))

    branches = manifest.get("branches", [])
    if isinstance(branches, list) and manifest.get("branch_count") != len(branches):
        errors.append(_finding(root / "manifest.json", "branch_count must match branches length."))


def _validate_project_status(
    status: dict[str, Any],
    root: Path,
    errors: list[ProjectPackageValidationFinding],
) -> None:
    checks = {
        "release_stage": "metadata-dry-run",
        "cloud_runnable": True,
        "dry_run_only": True,
        "data_downloaded": False,
        "no_download_enforced": True,
        "publishable_main_conclusion_supported": False,
        "extension_experiment_supported": False,
        "registry_passed": True,
    }
    for key, expected in checks.items():
        if status.get(key) != expected:
            errors.append(_finding(root / "project_status.json", f"{key} must be {expected!r}."))

    branches = status.get("branches", [])
    if not isinstance(branches, list) or not branches:
        errors.append(_finding(root / "project_status.json", "branches must be a non-empty list."))


def _validate_branch_package(
    branch: dict[str, Any],
    root: Path,
    checked_files: set[Path],
    errors: list[ProjectPackageValidationFinding],
) -> None:
    branch_id = branch.get("branch_id")
    workflow_id = branch.get("workflow_id")
    package_root = branch.get("package_root")
    if not isinstance(branch_id, str) or not branch_id:
        errors.append(_finding(root / "manifest.json", "branch_id is required."))
        return
    if not isinstance(workflow_id, str) or not workflow_id:
        errors.append(_finding(root / "manifest.json", f"{branch_id}: workflow_id is required."))
        return
    if not isinstance(package_root, str) or not package_root:
        errors.append(_finding(root / "manifest.json", f"{branch_id}: package_root is required."))
        return

    branch_root = root / package_root
    branch_status = _read_required_json(branch_root / "branch_status.json", root, checked_files, errors)
    evidence_manifest = _read_required_json(branch_root / "evidence" / "manifest.json", root, checked_files, errors)
    evidence_bundle = _read_required_json(branch_root / "evidence" / "evidence_bundle.json", root, checked_files, errors)
    if not branch_status or not evidence_manifest or not evidence_bundle:
        return

    if branch_status.get("branch_id") != branch_id:
        errors.append(_finding(branch_root / "branch_status.json", "branch_id does not match root manifest."))
    if branch_status.get("workflow_id") != workflow_id:
        errors.append(_finding(branch_root / "branch_status.json", "workflow_id does not match root manifest."))

    if evidence_manifest.get("workflow_id") != workflow_id:
        errors.append(_finding(branch_root / "evidence" / "manifest.json", "workflow_id does not match branch workflow."))
    if evidence_manifest.get("downloads_blocked") is not True:
        errors.append(_finding(branch_root / "evidence" / "manifest.json", "downloads_blocked must be true."))
    if evidence_manifest.get("data_downloaded") is not False:
        errors.append(_finding(branch_root / "evidence" / "manifest.json", "data_downloaded must be false."))

    if evidence_bundle.get("workflow_id") != workflow_id:
        errors.append(_finding(branch_root / "evidence" / "evidence_bundle.json", "workflow_id does not match branch workflow."))
    if evidence_bundle.get("downloads_blocked") is not True:
        errors.append(_finding(branch_root / "evidence" / "evidence_bundle.json", "downloads_blocked must be true."))
    if evidence_bundle.get("data_downloaded") is not False:
        errors.append(_finding(branch_root / "evidence" / "evidence_bundle.json", "data_downloaded must be false."))

    for relative_path in evidence_manifest.get("files", []):
        if not isinstance(relative_path, str):
            errors.append(_finding(branch_root / "evidence" / "manifest.json", "files entries must be strings."))
            continue
        path = branch_root / "evidence" / relative_path
        if not path.exists():
            errors.append(_finding(path, "File listed in branch evidence manifest does not exist."))

    for artifact in evidence_bundle.get("planned_artifacts", []):
        if not isinstance(artifact, str):
            errors.append(_finding(branch_root / "evidence" / "evidence_bundle.json", "planned_artifacts entries must be strings."))
            continue
        path = branch_root / "evidence" / "artifacts" / f"{artifact}.json"
        if not path.exists():
            errors.append(_finding(path, "Planned artifact file does not exist."))


def _scan_json_files(
    root: Path,
    checked_files: set[Path],
    errors: list[ProjectPackageValidationFinding],
) -> None:
    for path in root.rglob("*.json"):
        checked_files.add(path)
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_PACKAGE_TEXT:
            if forbidden in text:
                errors.append(_finding(path, f"Forbidden dry-run package text found: {forbidden}"))


def _read_required_json(
    path: Path,
    root: Path,
    checked_files: set[Path],
    errors: list[ProjectPackageValidationFinding],
) -> dict[str, Any] | None:
    checked_files.add(path)
    if not path.exists():
        errors.append(_finding(path, "Required JSON file is missing."))
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(_finding(path, f"Invalid JSON: {exc.msg}."))
        return None
    if not isinstance(payload, dict):
        errors.append(_finding(path, "JSON document must be an object."))
        return None
    return payload


def _result(
    root: Path,
    checked_files: set[Path],
    branch_count: int,
    errors: list[ProjectPackageValidationFinding],
    warnings: list[ProjectPackageValidationFinding],
) -> ProjectPackageValidationResult:
    return ProjectPackageValidationResult(
        passed=not errors,
        package_root=str(root),
        checked_file_count=len(checked_files),
        branch_count=branch_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _finding(path: Path, message: str) -> ProjectPackageValidationFinding:
    return ProjectPackageValidationFinding(
        severity="error",
        path=str(path),
        message=message,
    )
