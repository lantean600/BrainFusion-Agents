from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .datasets import DatasetRegistry
from .demo_runtime import SyntheticRuntimeResult, run_synthetic_runtime_demo
from .downloads import DownloadRunResult, materialize_tumor_downloads
from .package_validation import ProjectPackageValidationResult, validate_project_package
from .pipeline import MaterializedPipelineRun, materialize_pipeline_run
from .project_run import MaterializedProjectDryRunPackage, materialize_project_dry_run
from .project_status import ManifestInput


@dataclass(frozen=True)
class CloudJobResult:
    output_dir: Path
    download_run: DownloadRunResult | None
    project_package: MaterializedProjectDryRunPackage
    pipeline_run: MaterializedPipelineRun
    synthetic_runtime: SyntheticRuntimeResult
    project_package_validation: ProjectPackageValidationResult
    summary_path: Path
    files: tuple[Path, ...]

    @property
    def dry_run_only(self) -> bool:
        return not self.data_downloaded

    @property
    def data_downloaded(self) -> bool:
        return bool(self.download_run and self.download_run.data_downloaded)

    @property
    def downloads_blocked(self) -> bool:
        return self.download_run is None or not self.download_run.execute

    def to_dict(self) -> dict[str, Any]:
        ready_branches = [
            branch.branch_id
            for branch in self.pipeline_run.report.branches
            if branch.status == "ready"
        ]
        blocked_branches = [
            branch.branch_id
            for branch in self.pipeline_run.report.branches
            if branch.status != "ready"
        ]
        return {
            "output_dir": str(self.output_dir),
            "release_stage": _release_stage(self.data_downloaded),
            "cloud_runnable": self.project_package.status.cloud_runnable and self.project_package_validation.passed,
            "dry_run_only": self.dry_run_only,
            "data_downloaded": self.data_downloaded,
            "downloads_blocked": self.downloads_blocked,
            "download_dir": str(self.download_run.output_dir) if self.download_run else None,
            "download_summary": self.download_run.to_dict() if self.download_run else None,
            "project_package_dir": str(self.project_package.package_root),
            "pipeline_output_dir": str(self.pipeline_run.output_dir),
            "synthetic_runtime_dir": str(self.synthetic_runtime.output_dir),
            "summary_path": str(self.summary_path),
            "project_package_validation": self.project_package_validation.to_dict(),
            "project_branch_count": len(self.project_package.branches),
            "pipeline_branch_count": self.pipeline_run.report.branch_count,
            "synthetic_runtime_summary": self.synthetic_runtime.summary,
            "ready_pipeline_branches": ready_branches,
            "blocked_pipeline_branches": blocked_branches,
            "files": [str(path) for path in self.files],
        }


def run_cloud_job(
    registry: DatasetRegistry,
    output_dir: str | Path,
    *,
    pet_mr_manifest: ManifestInput = None,
    wsi_manifest: ManifestInput = None,
    ct_manifest: ManifestInput = None,
    pairing_manifest: ManifestInput = None,
    download_policy: str = "auto",
    download_dataset_ids: tuple[str, ...] | list[str] | None = None,
    download_plan: str | Path | None = None,
    max_download_mb: float = 1024.0,
) -> CloudJobResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if download_policy not in {"off", "plan", "auto"}:
        raise ValueError("download_policy must be one of: off, plan, auto.")

    download_run = None
    if download_policy != "off":
        download_run = materialize_tumor_downloads(
            root / "downloads",
            plan_path=download_plan,
            dataset_ids=download_dataset_ids,
            execute=download_policy == "auto",
            max_download_mb=max_download_mb,
        )
        if download_policy == "auto" and download_run.failed_count:
            failed = ", ".join(
                f"{result.dataset_id}: {result.message}"
                for result in download_run.results
                if result.status == "failed"
            )
            raise RuntimeError(f"Automatic tumor dataset download failed: {failed}")

    project_package = materialize_project_dry_run(
        registry,
        root / "project-dry-run",
        pet_mr_manifest=pet_mr_manifest,
        wsi_manifest=wsi_manifest,
        ct_manifest=ct_manifest,
        pairing_manifest=pairing_manifest,
    )
    pipeline_run = materialize_pipeline_run(
        registry,
        root / "pipeline-run",
        pet_mr_manifest=pet_mr_manifest,
        wsi_manifest=wsi_manifest,
        ct_manifest=ct_manifest,
        pairing_manifest=pairing_manifest,
    )
    synthetic_runtime = run_synthetic_runtime_demo(root / "synthetic-runtime")
    validation = validate_project_package(project_package.package_root)

    summary_path = root / "job_summary.json"
    summary = _summary_payload(root, download_run, project_package, pipeline_run, synthetic_runtime, validation)
    _write_json(summary_path, summary)

    download_files = download_run.files if download_run else ()
    files = (summary_path,) + download_files + project_package.files + pipeline_run.files + synthetic_runtime.files
    return CloudJobResult(
        output_dir=root,
        download_run=download_run,
        project_package=project_package,
        pipeline_run=pipeline_run,
        synthetic_runtime=synthetic_runtime,
        project_package_validation=validation,
        summary_path=summary_path,
        files=files,
    )


def _summary_payload(
    root: Path,
    download_run: DownloadRunResult | None,
    project_package: MaterializedProjectDryRunPackage,
    pipeline_run: MaterializedPipelineRun,
    synthetic_runtime: SyntheticRuntimeResult,
    validation: ProjectPackageValidationResult,
) -> dict[str, Any]:
    ready_branches = [
        branch.branch_id
        for branch in pipeline_run.report.branches
        if branch.status == "ready"
    ]
    blocked_branches = [
        {
            "branch_id": branch.branch_id,
            "workflow_id": branch.workflow_id,
            "blockers": list(branch.blockers),
        }
        for branch in pipeline_run.report.branches
        if branch.status != "ready"
    ]
    return {
        "schema_version": "brainfusion-cloud-job/v1",
        "release_stage": _release_stage(bool(download_run and download_run.data_downloaded)),
        "dry_run_only": not (download_run and download_run.data_downloaded),
        "data_downloaded": bool(download_run and download_run.data_downloaded),
        "downloads_blocked": download_run is None or not download_run.execute,
        "download_dir": str(download_run.output_dir.relative_to(root)) if download_run else None,
        "download_summary": download_run.to_dict() if download_run else None,
        "download_boundary": (
            "Tumor smoke datasets are downloaded only from explicit plan entries. "
            "TCIA/IDC/GDC full cohorts still require manifests, tokens, or platform tools."
        ),
        "project_package_dir": str(project_package.package_root.relative_to(root)),
        "pipeline_output_dir": str(pipeline_run.output_dir.relative_to(root)),
        "synthetic_runtime_dir": str(synthetic_runtime.output_dir.relative_to(root)),
        "synthetic_runtime_summary": synthetic_runtime.summary,
        "project_package_validation": validation.to_dict(),
        "project_branch_count": len(project_package.branches),
        "pipeline_branch_count": pipeline_run.report.branch_count,
        "ready_pipeline_branches": ready_branches,
        "blocked_pipeline_branches": blocked_branches,
        "publishable_main_conclusion_supported": project_package.status.publishable_main_conclusion_supported,
        "extension_experiment_supported": project_package.status.extension_experiment_supported,
        "cloud_runnable": project_package.status.cloud_runnable and validation.passed,
        "outputs": _outputs(download_run),
    }


def _outputs(download_run: DownloadRunResult | None) -> list[str]:
    values = [
        "job_summary.json",
        "project-dry-run/manifest.json",
        "project-dry-run/project_status.json",
        "pipeline-run/manifest.json",
        "pipeline-run/pipeline_report.json",
        "synthetic-runtime/manifest.json",
        "synthetic-runtime/demo_summary.json",
    ]
    if download_run:
        values.insert(1, "downloads/download_summary.json")
    return values


def _release_stage(data_downloaded: bool) -> str:
    return "cloud-job-download" if data_downloaded else "cloud-job-dry-run"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
