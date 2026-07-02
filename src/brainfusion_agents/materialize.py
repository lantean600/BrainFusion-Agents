from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evidence import DryRunEvidenceBundle


@dataclass(frozen=True)
class MaterializedEvidencePackage:
    package_root: Path
    files: tuple[Path, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_root": str(self.package_root),
            "files": [str(path) for path in self.files],
        }


def materialize_dry_run_evidence_bundle(
    bundle: DryRunEvidenceBundle,
    output_dir: str | Path,
) -> MaterializedEvidencePackage:
    root = Path(output_dir)
    traces_dir = root / "traces"
    artifacts_dir = root / "artifacts"
    traces_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []

    evidence_path = root / "evidence_bundle.json"
    _write_json(evidence_path, bundle.to_dict())
    files.append(evidence_path)

    for trace in bundle.traces:
        trace_path = traces_dir / f"{_file_slug(trace.trace_id)}.json"
        _write_json(trace_path, trace.to_dict())
        files.append(trace_path)

    for artifact in bundle.planned_artifacts:
        artifact_path = artifacts_dir / f"{artifact}.json"
        _write_json(
            artifact_path,
            {
                "artifact_id": artifact,
                "workflow_id": bundle.workflow_id,
                "status": bundle.artifact_status[artifact],
                "dataset_ids": list(bundle.dataset_ids),
                "dataset_names": list(bundle.dataset_names),
                "data_downloaded": False,
                "downloads_blocked": bundle.downloads_blocked,
                "source_records": [f"dataset:{dataset_id}" for dataset_id in bundle.dataset_ids],
                "limitations": list(bundle.limitations),
            },
        )
        files.append(artifact_path)

    manifest_path = root / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "brainfusion-dry-run-evidence/v1",
            "workflow_id": bundle.workflow_id,
            "route_claim_level": bundle.route_claim_level,
            "dataset_ids": list(bundle.dataset_ids),
            "dataset_names": list(bundle.dataset_names),
            "downloads_blocked": bundle.downloads_blocked,
            "data_downloaded": bundle.data_downloaded,
            "planned_artifact_count": len(bundle.planned_artifacts),
            "trace_count": len(bundle.traces),
            "files": [str(path.relative_to(root)) for path in files],
        },
    )
    files.insert(0, manifest_path)

    return MaterializedEvidencePackage(package_root=root, files=tuple(files))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _file_slug(value: str) -> str:
    return (
        value.lower()
        .replace(":", "_")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "-")
    )

