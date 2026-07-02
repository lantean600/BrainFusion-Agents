from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


@dataclass(frozen=True)
class SyntheticRuntimeResult:
    output_dir: Path
    summary_path: Path
    files: tuple[Path, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "summary_path": str(self.summary_path),
            "synthetic_data": True,
            "dry_run_only": True,
            "data_downloaded": False,
            "downloads_blocked": True,
            "files": [str(path) for path in self.files],
            "summary": self.summary,
        }


def run_synthetic_runtime_demo(
    output_dir: str | Path,
    *,
    subject_count: int = 3,
    seed: int = 20240702,
) -> SyntheticRuntimeResult:
    if subject_count < 1:
        raise ValueError("subject_count must be at least 1.")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    pet_mr_records = [_pet_mr_record(index, rng) for index in range(subject_count)]
    ct_records = [_ct_record(index, rng) for index in range(subject_count)]
    wsi_records = [_wsi_record(index, rng) for index in range(subject_count)]

    pet_mr_path = root / "pet_mr_fusion_demo.json"
    ct_path = root / "ct_preprocessing_demo.json"
    wsi_path = root / "wsi_preprocessing_demo.json"
    summary_path = root / "demo_summary.json"
    manifest_path = root / "manifest.json"

    _write_json(
        pet_mr_path,
        {
            "schema_version": "brainfusion-synthetic-pet-mr/v1",
            "synthetic_data": True,
            "data_downloaded": False,
            "downloads_blocked": True,
            "records": pet_mr_records,
        },
    )
    _write_json(
        ct_path,
        {
            "schema_version": "brainfusion-synthetic-ct/v1",
            "synthetic_data": True,
            "data_downloaded": False,
            "downloads_blocked": True,
            "records": ct_records,
        },
    )
    _write_json(
        wsi_path,
        {
            "schema_version": "brainfusion-synthetic-wsi/v1",
            "synthetic_data": True,
            "data_downloaded": False,
            "downloads_blocked": True,
            "records": wsi_records,
        },
    )

    summary = _summary(pet_mr_records, ct_records, wsi_records, subject_count, seed)
    _write_json(summary_path, summary)

    files = (manifest_path, summary_path, pet_mr_path, ct_path, wsi_path)
    _write_json(
        manifest_path,
        {
            "schema_version": "brainfusion-synthetic-runtime/v1",
            "release_stage": "synthetic-runtime-demo",
            "synthetic_data": True,
            "dry_run_only": True,
            "data_downloaded": False,
            "downloads_blocked": True,
            "subject_count": subject_count,
            "seed": seed,
            "files": [str(path.relative_to(root)) for path in files[1:]],
        },
    )

    return SyntheticRuntimeResult(
        output_dir=root,
        summary_path=summary_path,
        files=files,
        summary=summary,
    )


def _pet_mr_record(index: int, rng: random.Random) -> dict[str, Any]:
    subject_id = f"SYN-PETMR-{index + 1:03d}"
    pet = _volume(shape=(6, 12, 12), base=1.5 + index * 0.1, signal=2.0, rng=rng)
    mr = _volume(shape=(6, 12, 12), base=90.0 + index * 3.0, signal=35.0, rng=rng)
    pet_z = _zscore(pet)
    mr_norm = _minmax(mr)
    fused = [(pet_value + mr_value) / 2.0 for pet_value, mr_value in zip(pet_z, mr_norm)]
    high_signal = _fraction_above(fused, _mean(fused) + _std(fused))
    return {
        "subject_id": subject_id,
        "session_id": "synthetic-baseline",
        "workflow": "pet_mr_fusion",
        "voxel_count": len(fused),
        "alignment_status": "shape-matched",
        "pet_preprocessing": "zscore",
        "mr_preprocessing": "minmax",
        "fusion_method": "late-feature-average",
        "pet_mean": round(_mean(pet), 6),
        "mr_mean": round(_mean(mr), 6),
        "fused_mean": round(_mean(fused), 6),
        "fused_std": round(_std(fused), 6),
        "high_signal_fraction": round(high_signal, 6),
        "qc_status": "pass",
        "claim_boundary": "synthetic smoke test only",
    }


def _ct_record(index: int, rng: random.Random) -> dict[str, Any]:
    case_id = f"SYN-CT-{index + 1:03d}"
    ct = _volume(shape=(5, 16, 16), base=-650.0 + index * 15.0, signal=420.0, rng=rng)
    ct_norm = _zscore(ct)
    threshold = _mean(ct_norm) + 1.75 * _std(ct_norm)
    high_density_fraction = _fraction_above(ct_norm, threshold)
    return {
        "case_id": case_id,
        "workflow": "ct_preprocessing",
        "slice_count": 5,
        "voxel_count": len(ct),
        "normalization": "zscore",
        "intensity_mean_hu": round(_mean(ct), 6),
        "intensity_std_hu": round(_std(ct), 6),
        "high_density_fraction": round(high_density_fraction, 6),
        "candidate_lesion_count": max(1, round(high_density_fraction * 100)),
        "feature_vector": [
            round(_mean(ct_norm), 6),
            round(_std(ct_norm), 6),
            round(high_density_fraction, 6),
        ],
        "qc_status": "pass",
        "claim_boundary": "synthetic smoke test only",
    }


def _wsi_record(index: int, rng: random.Random) -> dict[str, Any]:
    slide_id = f"SYN-WSI-{index + 1:03d}"
    tiles = [_tile(tile_index, rng) for tile_index in range(32)]
    tissue_tiles = [tile for tile in tiles if tile["tissue_fraction"] >= 0.3 and tile["artifact_score"] <= 0.75]
    stain_means = [
        _mean([tile["stain_rgb"][channel] for tile in tissue_tiles]) if tissue_tiles else 0.0
        for channel in range(3)
    ]
    embedding = _embedding(tissue_tiles, stain_means)
    return {
        "slide_id": slide_id,
        "workflow": "wsi_preprocessing",
        "tile_count": len(tiles),
        "tissue_tile_count": len(tissue_tiles),
        "artifact_filtered_count": len(tiles) - len(tissue_tiles),
        "stain_normalization": "channel-mean-centering",
        "mean_tissue_fraction": round(_mean([tile["tissue_fraction"] for tile in tiles]), 6),
        "mean_artifact_score": round(_mean([tile["artifact_score"] for tile in tiles]), 6),
        "stain_mean_rgb": [round(value, 6) for value in stain_means],
        "embedding_model": "synthetic-tile-statistics",
        "embedding": [round(value, 6) for value in embedding],
        "qc_status": "pass" if tissue_tiles else "needs-human-review",
        "claim_boundary": "synthetic smoke test only",
    }


def _volume(
    *,
    shape: tuple[int, int, int],
    base: float,
    signal: float,
    rng: random.Random,
) -> list[float]:
    depth, height, width = shape
    center = ((depth - 1) / 2.0, (height - 1) / 2.0, (width - 1) / 2.0)
    scale = max(shape) / 3.0
    values: list[float] = []
    for z in range(depth):
        for y in range(height):
            for x in range(width):
                distance = math.sqrt((z - center[0]) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2)
                blob = signal * math.exp(-((distance / scale) ** 2))
                noise = rng.uniform(-0.08 * abs(signal), 0.08 * abs(signal))
                values.append(base + blob + noise)
    return values


def _tile(tile_index: int, rng: random.Random) -> dict[str, Any]:
    tissue_fraction = min(1.0, max(0.0, rng.betavariate(2.2, 2.0)))
    artifact_score = min(1.0, max(0.0, rng.betavariate(1.3, 4.0)))
    stain_rgb = (
        0.55 + 0.25 * tissue_fraction + rng.uniform(-0.04, 0.04),
        0.38 + 0.18 * tissue_fraction + rng.uniform(-0.04, 0.04),
        0.62 - 0.15 * artifact_score + rng.uniform(-0.04, 0.04),
    )
    return {
        "tile_id": f"tile-{tile_index + 1:03d}",
        "tissue_fraction": tissue_fraction,
        "artifact_score": artifact_score,
        "stain_rgb": stain_rgb,
    }


def _embedding(tissue_tiles: list[dict[str, Any]], stain_means: list[float]) -> list[float]:
    if not tissue_tiles:
        return [0.0] * 8
    tissue_values = [tile["tissue_fraction"] for tile in tissue_tiles]
    artifact_values = [tile["artifact_score"] for tile in tissue_tiles]
    return [
        _mean(tissue_values),
        _std(tissue_values),
        _mean(artifact_values),
        _std(artifact_values),
        stain_means[0],
        stain_means[1],
        stain_means[2],
        len(tissue_tiles) / 32.0,
    ]


def _summary(
    pet_mr_records: list[dict[str, Any]],
    ct_records: list[dict[str, Any]],
    wsi_records: list[dict[str, Any]],
    subject_count: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "schema_version": "brainfusion-synthetic-runtime-summary/v1",
        "release_stage": "synthetic-runtime-demo",
        "synthetic_data": True,
        "dry_run_only": True,
        "data_downloaded": False,
        "downloads_blocked": True,
        "subject_count": subject_count,
        "seed": seed,
        "pet_mr_fusion_records": len(pet_mr_records),
        "ct_preprocessing_records": len(ct_records),
        "wsi_preprocessing_records": len(wsi_records),
        "mean_pet_mr_high_signal_fraction": round(
            _mean([record["high_signal_fraction"] for record in pet_mr_records]),
            6,
        ),
        "mean_ct_high_density_fraction": round(
            _mean([record["high_density_fraction"] for record in ct_records]),
            6,
        ),
        "mean_wsi_tissue_tiles": round(
            _mean([record["tissue_tile_count"] for record in wsi_records]),
            6,
        ),
        "claim_boundary": "Synthetic smoke data proves runtime execution only; it does not support clinical or publication claims.",
    }


def _zscore(values: list[float]) -> list[float]:
    center = _mean(values)
    spread = _std(values)
    return [(value - center) / spread for value in values]


def _minmax(values: list[float]) -> list[float]:
    low = min(values)
    high = max(values)
    width = high - low
    if width == 0:
        return [0.0 for _ in values]
    return [(value - low) / width for value in values]


def _fraction_above(values: list[float], threshold: float) -> float:
    return sum(1 for value in values if value > threshold) / len(values)


def _mean(values: list[float] | list[int]) -> float:
    return float(mean(values)) if values else 0.0


def _std(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0
    spread = pstdev(values)
    return float(spread) if spread > 0 else 1.0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
