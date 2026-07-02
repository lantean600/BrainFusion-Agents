from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


ALLOWED_ACCESS_STATUSES = {
    "not-requested",
    "requested",
    "approved",
    "downloaded",
    "indexed",
    "excluded",
}


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    name: str
    modalities: tuple[str, ...]
    branch: str
    role: str
    access_status: str
    source_urls: tuple[str, ...]
    pairing_status: str
    notes: str = ""

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "DatasetRecord":
        required = {
            "dataset_id",
            "name",
            "modalities",
            "branch",
            "role",
            "access_status",
            "source_urls",
            "pairing_status",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"Dataset record missing fields: {', '.join(missing)}")
        access_status = str(raw["access_status"])
        if access_status not in ALLOWED_ACCESS_STATUSES:
            raise ValueError(f"Invalid access_status for {raw['dataset_id']}: {access_status}")
        source_urls = tuple(str(url) for url in raw["source_urls"])
        if not source_urls:
            raise ValueError(f"Dataset record {raw['dataset_id']} must keep source links")
        if "local_path" in raw or "download_path" in raw:
            raise ValueError(
                f"Dataset record {raw['dataset_id']} must not point at local downloaded data"
            )
        return cls(
            dataset_id=str(raw["dataset_id"]),
            name=str(raw["name"]),
            modalities=tuple(str(modality).upper() for modality in raw["modalities"]),
            branch=str(raw["branch"]),
            role=str(raw["role"]),
            access_status=access_status,
            source_urls=source_urls,
            pairing_status=str(raw["pairing_status"]),
            notes=str(raw.get("notes", "")),
        )


class DatasetRegistry:
    def __init__(self, records: list[DatasetRecord]):
        self._records = {record.dataset_id: record for record in records}
        if len(self._records) != len(records):
            raise ValueError("Duplicate dataset_id in registry")

    @classmethod
    def load(cls, path: str | Path) -> "DatasetRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_payload(payload)

    @classmethod
    def load_bundled(cls) -> "DatasetRegistry":
        payload = json.loads(
            files("brainfusion_agents")
            .joinpath("data/dataset_registry.json")
            .read_text(encoding="utf-8")
        )
        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DatasetRegistry":
        records = [DatasetRecord.from_mapping(raw) for raw in payload.get("datasets", [])]
        return cls(records)

    def list(self) -> tuple[DatasetRecord, ...]:
        return tuple(self._records.values())

    def get(self, dataset_id: str) -> DatasetRecord:
        try:
            return self._records[dataset_id]
        except KeyError as exc:
            raise KeyError(f"Unknown dataset_id: {dataset_id}") from exc

    def by_modality(self, modality: str) -> tuple[DatasetRecord, ...]:
        normalized = modality.upper()
        return tuple(
            record for record in self._records.values() if normalized in record.modalities
        )

    def by_branch(self, branch: str) -> tuple[DatasetRecord, ...]:
        return tuple(record for record in self._records.values() if record.branch == branch)
