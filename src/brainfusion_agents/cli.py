from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .audit import audit_dataset_registry
from .cloud_job import run_cloud_job
from .ct_manifest import ct_manifest_template, validate_ct_manifest
from .datasets import DatasetRegistry
from .demo_runtime import run_synthetic_runtime_demo
from .downloads import materialize_tumor_downloads
from .evidence import build_dry_run_evidence_bundle
from .manifest import case_selection_manifest_template, validate_case_selection_manifest
from .materialize import materialize_dry_run_evidence_bundle
from .pairing import PairingEvidence, evaluate_pairing_gate
from .pairing_manifest import pairing_manifest_template, validate_pairing_manifest
from .package_validation import validate_project_package
from .pipeline import materialize_pipeline_run
from .plans import build_workflow_plan
from .project_status import build_project_status_report
from .project_run import materialize_project_dry_run
from .readiness import (
    build_ct_readiness_report,
    build_pet_mr_readiness_report,
    build_wsi_readiness_report,
)
from .workflow import WorkflowRequest, plan_workflows, route_workflow
from .wsi_manifest import validate_wsi_manifest, wsi_manifest_template


DEFAULT_REGISTRY = Path("data/dataset_registry.json")
DEFAULT_CLOUD_OUTPUT_DIR = Path("outputs/project-dry-run")
DEFAULT_CLOUD_JOB_OUTPUT_DIR = Path("outputs/cloud-job")
DEFAULT_SYNTHETIC_RUNTIME_OUTPUT_DIR = Path("outputs/synthetic-runtime")
DEFAULT_DOWNLOAD_OUTPUT_DIR = Path("outputs/tumor-downloads")
DEFAULT_DOWNLOAD_PLAN = Path("data/tumor_download_plan.json")
SAMPLE_MANIFESTS = {
    "pet_mr_manifest": Path("examples/manifests/adni-case-selection.sample.json"),
    "wsi_manifest": Path("examples/manifests/tcga-wsi-preprocessing.sample.json"),
    "ct_manifest": Path("examples/manifests/lidc-ct-prototype.sample.json"),
    "pairing_manifest": Path("examples/manifests/ct-wsi-pairing-audit.sample.json"),
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = args.func(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brainfusion-agents",
        description="BrainFusion-Agents workflow kernel CLI.",
    )
    subparsers = parser.add_subparsers(required=True)

    datasets = subparsers.add_parser("datasets", help="List dataset registry records.")
    datasets.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    datasets.add_argument("--modality")
    datasets.add_argument("--branch")
    datasets.set_defaults(func=_datasets)

    audit = subparsers.add_parser(
        "audit-registry",
        help="Audit dataset registry against no-download and dataset strategy rules.",
    )
    audit.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    audit.set_defaults(func=_audit_registry)

    manifest_template = subparsers.add_parser(
        "manifest-template",
        help="Print a PET/MR case selection manifest template.",
    )
    manifest_template.set_defaults(func=_manifest_template)

    validate_manifest = subparsers.add_parser(
        "validate-manifest",
        help="Validate a PET/MR case selection manifest JSON file.",
    )
    validate_manifest.add_argument("--manifest", required=True)
    validate_manifest.set_defaults(func=_validate_manifest)

    pairing_manifest = subparsers.add_parser(
        "pairing-manifest-template",
        help="Print a CT-pathology pairing audit manifest template.",
    )
    pairing_manifest.set_defaults(func=_pairing_manifest_template)

    validate_pairing = subparsers.add_parser(
        "validate-pairing-manifest",
        help="Validate a CT-pathology pairing audit manifest JSON file.",
    )
    validate_pairing.add_argument("--manifest", required=True)
    validate_pairing.set_defaults(func=_validate_pairing_manifest)

    wsi_manifest = subparsers.add_parser(
        "wsi-manifest-template",
        help="Print a WSI preprocessing manifest template.",
    )
    wsi_manifest.set_defaults(func=_wsi_manifest_template)

    validate_wsi = subparsers.add_parser(
        "validate-wsi-manifest",
        help="Validate a WSI preprocessing manifest JSON file.",
    )
    validate_wsi.add_argument("--manifest", required=True)
    validate_wsi.set_defaults(func=_validate_wsi_manifest)

    ct_manifest = subparsers.add_parser(
        "ct-manifest-template",
        help="Print a CT prototype manifest template.",
    )
    ct_manifest.set_defaults(func=_ct_manifest_template)

    validate_ct = subparsers.add_parser(
        "validate-ct-manifest",
        help="Validate a CT prototype manifest JSON file.",
    )
    validate_ct.add_argument("--manifest", required=True)
    validate_ct.set_defaults(func=_validate_ct_manifest)

    readiness = subparsers.add_parser(
        "pet-mr-readiness",
        help="Build a PET/MR metadata readiness report from dataset IDs and a case selection manifest.",
    )
    readiness.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    readiness.add_argument("--dataset-ids", nargs="+", required=True)
    readiness.add_argument("--manifest", required=True)
    readiness.set_defaults(func=_pet_mr_readiness)

    wsi_readiness = subparsers.add_parser(
        "wsi-readiness",
        help="Build a WSI metadata readiness report from dataset IDs and a WSI preprocessing manifest.",
    )
    wsi_readiness.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    wsi_readiness.add_argument("--dataset-ids", nargs="+", required=True)
    wsi_readiness.add_argument("--manifest", required=True)
    wsi_readiness.set_defaults(func=_wsi_readiness)

    ct_readiness = subparsers.add_parser(
        "ct-readiness",
        help="Build a CT metadata readiness report from dataset IDs and a CT prototype manifest.",
    )
    ct_readiness.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ct_readiness.add_argument("--dataset-ids", nargs="+", required=True)
    ct_readiness.add_argument("--manifest", required=True)
    ct_readiness.set_defaults(func=_ct_readiness)

    project_status = subparsers.add_parser(
        "project-status",
        help="Build a project-level cloud dry-run status report.",
    )
    project_status.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    project_status.add_argument("--pet-mr-manifest")
    project_status.add_argument("--wsi-manifest")
    project_status.add_argument("--ct-manifest")
    project_status.add_argument("--pairing-manifest")
    project_status.set_defaults(func=_project_status)

    materialize_project = subparsers.add_parser(
        "materialize-project-dry-run",
        help="Write a project-level dry-run evidence package for cloud execution checks.",
    )
    materialize_project.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    materialize_project.add_argument("--output-dir", required=True)
    materialize_project.add_argument("--pet-mr-manifest")
    materialize_project.add_argument("--wsi-manifest")
    materialize_project.add_argument("--ct-manifest")
    materialize_project.add_argument("--pairing-manifest")
    materialize_project.set_defaults(func=_materialize_project_dry_run)

    cloud_run = subparsers.add_parser(
        "cloud-run",
        help="Run the default cloud dry-run job and write a project evidence package.",
    )
    cloud_run.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    cloud_run.add_argument("--output-dir", default=str(DEFAULT_CLOUD_OUTPUT_DIR))
    cloud_run.add_argument(
        "--no-sample-manifests",
        action="store_true",
        help="Do not auto-use included examples/manifests sample files.",
    )
    cloud_run.set_defaults(func=_cloud_run)

    cloud_job = subparsers.add_parser(
        "cloud-job",
        help="Run the full cloud dry-run job and write project, pipeline, and summary outputs.",
    )
    cloud_job.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    cloud_job.add_argument("--output-dir", default=str(DEFAULT_CLOUD_JOB_OUTPUT_DIR))
    cloud_job.add_argument("--pet-mr-manifest")
    cloud_job.add_argument("--wsi-manifest")
    cloud_job.add_argument("--ct-manifest")
    cloud_job.add_argument("--pairing-manifest")
    cloud_job.add_argument(
        "--download-policy",
        choices=("off", "plan", "auto"),
        default="auto",
        help="Tumor dataset download behavior. Default auto downloads public smoke datasets.",
    )
    cloud_job.add_argument("--download-plan", default=str(DEFAULT_DOWNLOAD_PLAN))
    cloud_job.add_argument("--download-datasets", nargs="+")
    cloud_job.add_argument("--max-download-mb", type=float, default=1024.0)
    cloud_job.add_argument(
        "--no-sample-manifests",
        action="store_true",
        help="Do not auto-use included examples/manifests sample files.",
    )
    cloud_job.set_defaults(func=_cloud_job)

    synthetic_demo = subparsers.add_parser(
        "synthetic-demo",
        help="Run a no-download synthetic PET/MR, CT, and WSI runtime smoke test.",
    )
    synthetic_demo.add_argument("--output-dir", default=str(DEFAULT_SYNTHETIC_RUNTIME_OUTPUT_DIR))
    synthetic_demo.add_argument("--subject-count", type=int, default=3)
    synthetic_demo.add_argument("--seed", type=int, default=20240702)
    synthetic_demo.set_defaults(func=_synthetic_demo)

    download_data = subparsers.add_parser(
        "download-data",
        help="Materialize or execute the tumor-first dataset download plan.",
    )
    download_data.add_argument("--plan", default=str(DEFAULT_DOWNLOAD_PLAN))
    download_data.add_argument("--output-dir", default=str(DEFAULT_DOWNLOAD_OUTPUT_DIR))
    download_data.add_argument("--dataset-ids", nargs="+")
    download_data.add_argument("--max-download-mb", type=float, default=1024.0)
    download_data.add_argument(
        "--execute",
        action="store_true",
        help="Actually download direct public datasets. Without this flag only writes a plan.",
    )
    download_data.set_defaults(func=_download_data)

    validate_project = subparsers.add_parser(
        "validate-project-package",
        help="Validate a materialized project dry-run evidence package.",
    )
    validate_project.add_argument("--package-dir", required=True)
    validate_project.set_defaults(func=_validate_project_package)

    run_pipeline = subparsers.add_parser(
        "run-pipeline",
        help="Run the medical imaging preprocessing and fusion dry-run pipeline.",
    )
    run_pipeline.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    run_pipeline.add_argument("--output-dir", required=True)
    run_pipeline.add_argument("--pet-mr-manifest")
    run_pipeline.add_argument("--wsi-manifest")
    run_pipeline.add_argument("--ct-manifest")
    run_pipeline.add_argument("--pairing-manifest")
    run_pipeline.add_argument(
        "--no-sample-manifests",
        action="store_true",
        help="Do not auto-use included examples/manifests sample files.",
    )
    run_pipeline.set_defaults(func=_run_pipeline)

    route = subparsers.add_parser("route", help="Route a single modality availability case.")
    route.add_argument("--modalities", nargs="+", required=True)
    route.add_argument("--pairing-verified", action="store_true")
    route.add_argument("--pairing-level", default="none")
    route.set_defaults(func=_route)

    plan = subparsers.add_parser("plan", help="Plan all workflows implied by modalities.")
    plan.add_argument("--modalities", nargs="+", required=True)
    plan.add_argument("--pairing-verified", action="store_true")
    plan.add_argument("--pairing-level", default="none")
    plan.set_defaults(func=_plan)

    plan_datasets = subparsers.add_parser(
        "plan-datasets",
        help="Build an executable workflow plan from dataset registry IDs.",
    )
    plan_datasets.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    plan_datasets.add_argument("--dataset-ids", nargs="+", required=True)
    plan_datasets.add_argument("--pairing-verified", action="store_true")
    plan_datasets.add_argument("--pairing-level", default="none")
    plan_datasets.set_defaults(func=_plan_datasets)

    dry_run = subparsers.add_parser(
        "dry-run-evidence",
        help="Build a dry-run evidence bundle from dataset registry IDs.",
    )
    dry_run.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    dry_run.add_argument("--dataset-ids", nargs="+", required=True)
    dry_run.add_argument("--pairing-verified", action="store_true")
    dry_run.add_argument("--pairing-level", default="none")
    dry_run.set_defaults(func=_dry_run_evidence)

    materialize = subparsers.add_parser(
        "materialize-dry-run",
        help="Write a dry-run evidence package to a local output directory.",
    )
    materialize.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    materialize.add_argument("--dataset-ids", nargs="+", required=True)
    materialize.add_argument("--output-dir", required=True)
    materialize.add_argument("--pairing-verified", action="store_true")
    materialize.add_argument("--pairing-level", default="none")
    materialize.set_defaults(func=_materialize_dry_run)

    gate = subparsers.add_parser("pairing-gate", help="Evaluate CT-pathology pairing evidence.")
    gate.add_argument("--sources", nargs="+", required=True)
    gate.add_argument("--identifier-fields", nargs="*", default=[])
    gate.add_argument("--paired-patients", type=int, default=0)
    gate.add_argument("--paired-lesions", type=int)
    gate.add_argument("--timing-assumption")
    gate.add_argument("--endpoint-available", action="store_true")
    gate.set_defaults(func=_pairing_gate)

    return parser


def _load_registry(path: str) -> DatasetRegistry:
    registry_path = Path(path)
    if path == str(DEFAULT_REGISTRY) and not registry_path.exists():
        return DatasetRegistry.load_bundled()
    return DatasetRegistry.load(registry_path)


def _datasets(args: argparse.Namespace) -> list[dict[str, Any]]:
    registry = _load_registry(args.registry)
    if args.modality:
        records = registry.by_modality(args.modality)
    elif args.branch:
        records = registry.by_branch(args.branch)
    else:
        records = registry.list()
    return [asdict(record) for record in records]


def _audit_registry(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return audit_dataset_registry(registry).to_dict()


def _manifest_template(args: argparse.Namespace) -> dict[str, Any]:
    return case_selection_manifest_template()


def _validate_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return validate_case_selection_manifest(args.manifest).to_dict()


def _pairing_manifest_template(args: argparse.Namespace) -> dict[str, Any]:
    return pairing_manifest_template()


def _validate_pairing_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return validate_pairing_manifest(args.manifest).to_dict()


def _wsi_manifest_template(args: argparse.Namespace) -> dict[str, Any]:
    return wsi_manifest_template()


def _validate_wsi_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return validate_wsi_manifest(args.manifest).to_dict()


def _ct_manifest_template(args: argparse.Namespace) -> dict[str, Any]:
    return ct_manifest_template()


def _validate_ct_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return validate_ct_manifest(args.manifest).to_dict()


def _pet_mr_readiness(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return build_pet_mr_readiness_report(
        registry,
        args.dataset_ids,
        args.manifest,
    ).to_dict()


def _wsi_readiness(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return build_wsi_readiness_report(
        registry,
        args.dataset_ids,
        args.manifest,
    ).to_dict()


def _ct_readiness(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return build_ct_readiness_report(
        registry,
        args.dataset_ids,
        args.manifest,
    ).to_dict()


def _project_status(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return build_project_status_report(
        registry,
        pet_mr_manifest=args.pet_mr_manifest,
        wsi_manifest=args.wsi_manifest,
        ct_manifest=args.ct_manifest,
        pairing_manifest=args.pairing_manifest,
    ).to_dict()


def _materialize_project_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return materialize_project_dry_run(
        registry,
        args.output_dir,
        pet_mr_manifest=args.pet_mr_manifest,
        wsi_manifest=args.wsi_manifest,
        ct_manifest=args.ct_manifest,
        pairing_manifest=args.pairing_manifest,
    ).to_dict()


def _cloud_run(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    manifests = _cloud_sample_manifests(use_samples=not args.no_sample_manifests)
    return materialize_project_dry_run(
        registry,
        args.output_dir,
        **manifests,
    ).to_dict()


def _cloud_job(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    manifests = _cloud_sample_manifests(use_samples=not args.no_sample_manifests)
    return run_cloud_job(
        registry,
        args.output_dir,
        pet_mr_manifest=args.pet_mr_manifest or manifests["pet_mr_manifest"],
        wsi_manifest=args.wsi_manifest or manifests["wsi_manifest"],
        ct_manifest=args.ct_manifest or manifests["ct_manifest"],
        pairing_manifest=args.pairing_manifest or manifests["pairing_manifest"],
        download_policy=args.download_policy,
        download_dataset_ids=args.download_datasets,
        download_plan=_resolve_download_plan(args.download_plan),
        max_download_mb=args.max_download_mb,
    ).to_dict()


def _synthetic_demo(args: argparse.Namespace) -> dict[str, Any]:
    return run_synthetic_runtime_demo(
        args.output_dir,
        subject_count=args.subject_count,
        seed=args.seed,
    ).to_dict()


def _download_data(args: argparse.Namespace) -> dict[str, Any]:
    return materialize_tumor_downloads(
        args.output_dir,
        plan_path=_resolve_download_plan(args.plan),
        dataset_ids=args.dataset_ids,
        execute=args.execute,
        max_download_mb=args.max_download_mb,
    ).to_dict()


def _validate_project_package(args: argparse.Namespace) -> dict[str, Any]:
    return validate_project_package(args.package_dir).to_dict()


def _run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    manifests = _cloud_sample_manifests(use_samples=not args.no_sample_manifests)
    return materialize_pipeline_run(
        registry,
        args.output_dir,
        pet_mr_manifest=args.pet_mr_manifest or manifests["pet_mr_manifest"],
        wsi_manifest=args.wsi_manifest or manifests["wsi_manifest"],
        ct_manifest=args.ct_manifest or manifests["ct_manifest"],
        pairing_manifest=args.pairing_manifest or manifests["pairing_manifest"],
    ).to_dict()


def _cloud_sample_manifests(*, use_samples: bool) -> dict[str, str | None]:
    if not use_samples:
        return {key: None for key in SAMPLE_MANIFESTS}
    return {
        key: _resolve_sample_manifest(path)
        for key, path in SAMPLE_MANIFESTS.items()
    }


def _resolve_sample_manifest(path: Path) -> str | None:
    if path.exists():
        return str(path)
    source_root_path = Path(__file__).resolve().parents[2] / path
    if source_root_path.exists():
        return str(source_root_path)
    packaged_path = Path(__file__).resolve().parent / "data" / "manifests" / path.name
    if packaged_path.exists():
        return str(packaged_path)
    return None


def _resolve_download_plan(path: str | None) -> str | None:
    if not path:
        return None
    plan_path = Path(path)
    if plan_path.exists():
        return str(plan_path)
    if path == str(DEFAULT_DOWNLOAD_PLAN):
        return None
    return path


def _route(args: argparse.Namespace) -> dict[str, Any]:
    request = WorkflowRequest.from_modalities(
        args.modalities,
        pairing_verified=args.pairing_verified,
        pairing_level=args.pairing_level,
    )
    return asdict(route_workflow(request))


def _plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    request = WorkflowRequest.from_modalities(
        args.modalities,
        pairing_verified=args.pairing_verified,
        pairing_level=args.pairing_level,
    )
    return [asdict(route) for route in plan_workflows(request)]


def _plan_datasets(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    return asdict(
        build_workflow_plan(
            registry,
            args.dataset_ids,
            pairing_verified=args.pairing_verified,
            pairing_level=args.pairing_level,
        )
    )


def _dry_run_evidence(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    bundle = build_dry_run_evidence_bundle(
        registry,
        args.dataset_ids,
        pairing_verified=args.pairing_verified,
        pairing_level=args.pairing_level,
    )
    return bundle.to_dict()


def _materialize_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registry(args.registry)
    bundle = build_dry_run_evidence_bundle(
        registry,
        args.dataset_ids,
        pairing_verified=args.pairing_verified,
        pairing_level=args.pairing_level,
    )
    package = materialize_dry_run_evidence_bundle(bundle, args.output_dir)
    return package.to_dict()


def _pairing_gate(args: argparse.Namespace) -> dict[str, Any]:
    result = evaluate_pairing_gate(
        PairingEvidence(
            source_datasets=tuple(args.sources),
            identifier_fields=tuple(args.identifier_fields),
            paired_patient_count=args.paired_patients,
            paired_lesion_count=args.paired_lesions,
            timing_assumption=args.timing_assumption,
            endpoint_available=args.endpoint_available,
        )
    )
    payload = asdict(result)
    payload["passed"] = result.passed
    return payload
