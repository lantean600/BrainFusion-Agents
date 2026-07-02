from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .datasets import DatasetRegistry
from .evidence import build_dry_run_evidence_bundle
from .materialize import MaterializedEvidencePackage, materialize_dry_run_evidence_bundle
from .project_status import ManifestInput, ProjectStatusReport, build_project_status_report


@dataclass(frozen=True)
class MaterializedProjectBranchPackage:
    branch_id: str
    workflow_id: str
    package_root: Path
    files: tuple[Path, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "workflow_id": self.workflow_id,
            "package_root": str(self.package_root),
            "files": [str(path) for path in self.files],
        }


@dataclass(frozen=True)
class MaterializedProjectDryRunPackage:
    package_root: Path
    status: ProjectStatusReport
    branches: tuple[MaterializedProjectBranchPackage, ...]
    files: tuple[Path, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_root": str(self.package_root),
            "release_stage": self.status.release_stage,
            "cloud_runnable": self.status.cloud_runnable,
            "dry_run_only": self.status.dry_run_only,
            "data_downloaded": self.status.data_downloaded,
            "no_download_enforced": self.status.no_download_enforced,
            "branches": [branch.to_dict() for branch in self.branches],
            "files": [str(path) for path in self.files],
        }


def materialize_project_dry_run(
    registry: DatasetRegistry,
    output_dir: str | Path,
    *,
    pet_mr_manifest: ManifestInput = None,
    wsi_manifest: ManifestInput = None,
    ct_manifest: ManifestInput = None,
    pairing_manifest: ManifestInput = None,
) -> MaterializedProjectDryRunPackage:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    status = build_project_status_report(
        registry,
        pet_mr_manifest=pet_mr_manifest,
        wsi_manifest=wsi_manifest,
        ct_manifest=ct_manifest,
        pairing_manifest=pairing_manifest,
    )

    files: list[Path] = []

    status_path = root / "project_status.json"
    _write_json(status_path, status.to_dict())
    files.append(status_path)

    branch_packages: list[MaterializedProjectBranchPackage] = []
    for branch in status.branches:
        package = _materialize_branch(registry, root, branch.to_dict())
        branch_packages.append(package)
        files.extend(package.files)

    manifest_path = root / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "brainfusion-project-dry-run/v1",
            "release_stage": status.release_stage,
            "cloud_runnable": status.cloud_runnable,
            "dry_run_only": status.dry_run_only,
            "data_downloaded": status.data_downloaded,
            "no_download_enforced": status.no_download_enforced,
            "publishable_main_conclusion_supported": status.publishable_main_conclusion_supported,
            "extension_experiment_supported": status.extension_experiment_supported,
            "branch_count": len(branch_packages),
            "branches": [
                {
                    "branch_id": branch.branch_id,
                    "workflow_id": branch.workflow_id,
                    "package_root": str(branch.package_root.relative_to(root)),
                    "file_count": len(branch.files),
                }
                for branch in branch_packages
            ],
            "files": [str(path.relative_to(root)) for path in files],
        },
    )
    files.insert(0, manifest_path)

    return MaterializedProjectDryRunPackage(
        package_root=root,
        status=status,
        branches=tuple(branch_packages),
        files=tuple(files),
    )


def _materialize_branch(
    registry: DatasetRegistry,
    root: Path,
    branch_payload: dict[str, Any],
) -> MaterializedProjectBranchPackage:
    branch_id = branch_payload["branch_id"]
    branch_root = root / "branches" / branch_id
    branch_root.mkdir(parents=True, exist_ok=True)

    status_path = branch_root / "branch_status.json"
    _write_json(status_path, branch_payload)

    evidence_package = _branch_evidence_package(registry, branch_root, branch_payload)
    files = (status_path,) + evidence_package.files

    return MaterializedProjectBranchPackage(
        branch_id=branch_id,
        workflow_id=branch_payload["workflow_id"],
        package_root=branch_root,
        files=files,
    )


def _branch_evidence_package(
    registry: DatasetRegistry,
    branch_root: Path,
    branch_payload: dict[str, Any],
) -> MaterializedEvidencePackage:
    pairing_verified = (
        branch_payload["workflow_id"] == "ct_pathology_fusion"
        and branch_payload.get("details", {}).get("gate_status") == "pass"
    )
    pairing_level = (
        branch_payload.get("details", {}).get("pairing_level", "none")
        if pairing_verified
        else "none"
    )
    bundle = build_dry_run_evidence_bundle(
        registry,
        tuple(branch_payload["dataset_ids"]),
        pairing_verified=pairing_verified,
        pairing_level=pairing_level,
    )
    if bundle.workflow_id != branch_payload["workflow_id"]:
        raise ValueError(
            f"Branch {branch_payload['branch_id']} status/evidence route mismatch: "
            f"{branch_payload['workflow_id']} != {bundle.workflow_id}"
        )
    return materialize_dry_run_evidence_bundle(bundle, branch_root / "evidence")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
