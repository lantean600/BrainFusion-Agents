from __future__ import annotations

import hashlib
import json
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


DIRECT_DOWNLOAD_METHOD = "direct-http"
DEFAULT_DOWNLOAD_PLAN = Path("data/tumor_download_plan.json")


@dataclass(frozen=True)
class DownloadDatasetSpec:
    dataset_id: str
    name: str
    modality_group: str
    tumor_context: str
    download_method: str
    url: str
    filename: str
    md5: str | None
    estimated_size_mb: float
    default_auto_download: bool
    license: str
    source: str
    notes: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "DownloadDatasetSpec":
        required = {
            "dataset_id",
            "name",
            "modality_group",
            "tumor_context",
            "download_method",
            "url",
            "filename",
            "estimated_size_mb",
            "default_auto_download",
            "license",
            "source",
            "notes",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"Download spec missing fields: {', '.join(missing)}")
        return cls(
            dataset_id=str(raw["dataset_id"]),
            name=str(raw["name"]),
            modality_group=str(raw["modality_group"]),
            tumor_context=str(raw["tumor_context"]),
            download_method=str(raw["download_method"]),
            url=str(raw["url"]),
            filename=str(raw["filename"]),
            md5=str(raw["md5"]) if raw.get("md5") else None,
            estimated_size_mb=float(raw["estimated_size_mb"]),
            default_auto_download=bool(raw["default_auto_download"]),
            license=str(raw["license"]),
            source=str(raw["source"]),
            notes=str(raw["notes"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "modality_group": self.modality_group,
            "tumor_context": self.tumor_context,
            "download_method": self.download_method,
            "url": self.url,
            "filename": self.filename,
            "md5": self.md5,
            "estimated_size_mb": self.estimated_size_mb,
            "default_auto_download": self.default_auto_download,
            "license": self.license,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DatasetDownloadResult:
    dataset_id: str
    status: str
    path: str | None
    bytes_written: int
    md5: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "status": self.status,
            "path": self.path,
            "bytes_written": self.bytes_written,
            "md5": self.md5,
            "message": self.message,
        }


@dataclass(frozen=True)
class DownloadRunResult:
    output_dir: Path
    execute: bool
    data_downloaded: bool
    download_count: int
    planned_count: int
    skipped_count: int
    failed_count: int
    manifest_path: Path
    summary_path: Path
    files: tuple[Path, ...]
    results: tuple[DatasetDownloadResult, ...]
    specs: tuple[DownloadDatasetSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "execute": self.execute,
            "data_downloaded": self.data_downloaded,
            "download_count": self.download_count,
            "planned_count": self.planned_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "manifest_path": str(self.manifest_path),
            "summary_path": str(self.summary_path),
            "files": [str(path) for path in self.files],
            "results": [result.to_dict() for result in self.results],
            "datasets": [spec.to_dict() for spec in self.specs],
        }


def load_download_specs(plan_path: str | Path | None = None) -> tuple[DownloadDatasetSpec, ...]:
    if plan_path is None:
        path = DEFAULT_DOWNLOAD_PLAN
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = json.loads(
                files("brainfusion_agents")
                .joinpath("data/tumor_download_plan.json")
                .read_text(encoding="utf-8")
            )
    else:
        payload = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    return tuple(DownloadDatasetSpec.from_mapping(raw) for raw in payload.get("datasets", []))


def materialize_tumor_downloads(
    output_dir: str | Path,
    *,
    plan_path: str | Path | None = None,
    dataset_ids: tuple[str, ...] | list[str] | None = None,
    execute: bool = False,
    max_download_mb: float = 1024.0,
) -> DownloadRunResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    selected_specs = _select_specs(load_download_specs(plan_path), dataset_ids)
    _check_size_budget(selected_specs, max_download_mb)

    results: list[DatasetDownloadResult] = []
    files_out: list[Path] = []
    downloads_root = root / "files"
    if execute:
        downloads_root.mkdir(parents=True, exist_ok=True)

    for spec in selected_specs:
        if spec.download_method != DIRECT_DOWNLOAD_METHOD:
            results.append(
                DatasetDownloadResult(
                    dataset_id=spec.dataset_id,
                    status="requires-external-manifest",
                    path=None,
                    bytes_written=0,
                    md5=None,
                    message=f"{spec.name} requires {spec.download_method}; {spec.notes}",
                )
            )
            continue
        if not execute:
            results.append(
                DatasetDownloadResult(
                    dataset_id=spec.dataset_id,
                    status="planned",
                    path=None,
                    bytes_written=0,
                    md5=spec.md5,
                    message="Pass execute=true or CLI --execute to download this dataset.",
                )
            )
            continue

        result = _download_direct(spec, downloads_root / spec.dataset_id)
        results.append(result)
        if result.path:
            files_out.append(Path(result.path))

    manifest_path = root / "download_manifest.json"
    summary_path = root / "download_summary.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "brainfusion-tumor-download-manifest/v1",
            "execute": execute,
            "max_download_mb": max_download_mb,
            "datasets": [spec.to_dict() for spec in selected_specs],
        },
    )
    summary = _summary(root, execute, selected_specs, results)
    _write_json(summary_path, summary)
    files_all = (manifest_path, summary_path) + tuple(files_out)
    return DownloadRunResult(
        output_dir=root,
        execute=execute,
        data_downloaded=summary["data_downloaded"],
        download_count=summary["download_count"],
        planned_count=summary["planned_count"],
        skipped_count=summary["skipped_count"],
        failed_count=summary["failed_count"],
        manifest_path=manifest_path,
        summary_path=summary_path,
        files=files_all,
        results=tuple(results),
        specs=selected_specs,
    )


def _select_specs(
    specs: tuple[DownloadDatasetSpec, ...],
    dataset_ids: tuple[str, ...] | list[str] | None,
) -> tuple[DownloadDatasetSpec, ...]:
    if dataset_ids:
        by_id = {spec.dataset_id: spec for spec in specs}
        missing = sorted(set(dataset_ids) - set(by_id))
        if missing:
            raise ValueError(f"Unknown download dataset_id(s): {', '.join(missing)}")
        return tuple(by_id[dataset_id] for dataset_id in dataset_ids)
    return tuple(spec for spec in specs if spec.default_auto_download)


def _check_size_budget(specs: tuple[DownloadDatasetSpec, ...], max_download_mb: float) -> None:
    estimated_total = sum(
        spec.estimated_size_mb
        for spec in specs
        if spec.download_method == DIRECT_DOWNLOAD_METHOD
    )
    if estimated_total > max_download_mb:
        raise ValueError(
            f"Selected tumor downloads estimate {estimated_total:.1f} MB, "
            f"above max_download_mb={max_download_mb:.1f}."
        )


def _download_direct(spec: DownloadDatasetSpec, dataset_dir: Path) -> DatasetDownloadResult:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    destination = dataset_dir / spec.filename
    if destination.exists():
        checksum = _md5(destination)
        if spec.md5 is None or checksum == spec.md5:
            return DatasetDownloadResult(
                dataset_id=spec.dataset_id,
                status="reused",
                path=str(destination),
                bytes_written=destination.stat().st_size,
                md5=checksum,
                message="Existing verified file reused.",
            )
        destination.unlink()

    partial = destination.with_suffix(destination.suffix + ".part")
    last_message = ""
    for attempt in range(1, 4):
        _safe_unlink(partial)
        try:
            _copy_url(spec.url, partial)
            bytes_written = partial.stat().st_size
            if bytes_written == 0:
                last_message = f"attempt {attempt}: downloaded file was empty"
                continue
            checksum = _md5(partial)
            if spec.md5 is not None and checksum != spec.md5:
                last_message = (
                    f"attempt {attempt}: MD5 mismatch for {spec.filename}: "
                    f"expected {spec.md5}, got {checksum}, bytes={bytes_written}"
                )
                continue
            shutil.copyfile(partial, destination)
            _safe_unlink(partial)
            return DatasetDownloadResult(
                dataset_id=spec.dataset_id,
                status="downloaded",
                path=str(destination),
                bytes_written=destination.stat().st_size,
                md5=checksum,
                message="Downloaded and verified.",
            )
        except Exception as exc:  # pragma: no cover - exercised in cloud/network environments
            last_message = f"attempt {attempt}: {exc}"

    _safe_unlink(partial)
    return DatasetDownloadResult(
        dataset_id=spec.dataset_id,
        status="failed",
        path=None,
        bytes_written=0,
        md5=None,
        message=f"Download failed after 3 attempts: {last_message}",
    )


def _copy_url(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"", "file"}:
        source = Path(urllib.request.url2pathname(parsed.path if parsed.scheme == "file" else url))
        shutil.copyfile(source, destination)
        return
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "brainfusion-agents/0.1 tumor-download"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)


def _summary(
    root: Path,
    execute: bool,
    specs: tuple[DownloadDatasetSpec, ...],
    results: list[DatasetDownloadResult],
) -> dict[str, Any]:
    downloaded = [result for result in results if result.status in {"downloaded", "reused"}]
    planned = [result for result in results if result.status == "planned"]
    skipped = [result for result in results if result.status == "requires-external-manifest"]
    failed = [result for result in results if result.status == "failed"]
    return {
        "schema_version": "brainfusion-tumor-download-summary/v1",
        "release_stage": "tumor-download",
        "output_dir": str(root),
        "execute": execute,
        "data_downloaded": bool(downloaded),
        "download_count": len(downloaded),
        "planned_count": len(planned),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "selected_dataset_ids": [spec.dataset_id for spec in specs],
        "tumor_first": True,
        "results": [result.to_dict() for result in results],
    }


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        pass


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
