# Cloud Run Guide

This project is currently a metadata-only dry-run kernel. It is suitable for a cloud compute platform before dataset access is approved because it does not download ADNI, OASIS-3, TCIA, GDC, CAMELYON, PANDA, or IGNITE files.

## Runtime

- Python 3.11+
- No Python package dependencies beyond the standard library
- Optional container runtime if the cloud platform launches Docker images

## Install on a Cloud VM

```bash
python -m pip install .
brainfusion-agents cloud-job --output-dir outputs/cloud-job
```

When launched from the repository root, the CLI reads `data/dataset_registry.json`. When launched from another directory after installation, it falls back to the packaged registry copy so cloud jobs do not depend on the current working directory.

The command should report:

- `cloud_runnable=true`
- `dry_run_only=true`
- `data_downloaded=false`
- a `job_summary.json` path plus project and pipeline output directories

## Run With Included No-Download Samples

```bash
brainfusion-agents project-status \
  --pet-mr-manifest examples/manifests/adni-case-selection.sample.json \
  --wsi-manifest examples/manifests/tcga-wsi-preprocessing.sample.json \
  --ct-manifest examples/manifests/lidc-ct-prototype.sample.json \
  --pairing-manifest examples/manifests/ct-wsi-pairing-audit.sample.json
```

Expected status:

- PET/MR, WSI, and CT metadata branches are ready for dry-run planning.
- CT-pathology fusion remains blocked because the included pairing audit sample intentionally has no verified paired patients.
- No main conclusion or extension experiment is supported in this no-download phase.

To create a collectable cloud job artifact, materialize the project dry run:

```bash
python -m brainfusion_agents cloud-job --output-dir outputs/cloud-job
```

`cloud-job` automatically uses the included sample manifests when `examples/manifests/` exists. It writes:

- `outputs/cloud-job/job_summary.json`
- `outputs/cloud-job/project-dry-run/manifest.json`
- `outputs/cloud-job/project-dry-run/project_status.json`
- `outputs/cloud-job/pipeline-run/manifest.json`
- `outputs/cloud-job/pipeline-run/pipeline_report.json`

Use this as the default command on AutoDL, RunPod, Lambda Labs, Slurm jobs, or a plain cloud VM. Pass `--no-sample-manifests` to generate the same package shape with manifest blockers instead.

To create only the project dry-run package:

```bash
python -m brainfusion_agents cloud-run --output-dir outputs/project-dry-run
```

`cloud-run` automatically uses the included sample manifests when `examples/manifests/` exists. Pass `--no-sample-manifests` to generate the same package shape with manifest blockers instead.

To run the medical imaging preprocessing and fusion pipeline:

```bash
python -m brainfusion_agents run-pipeline --output-dir outputs/pipeline-run
```

The pipeline output contains `pipeline_report.json` plus task-level artifacts for PET/MR fusion planning, WSI tissue/patch/embedding planning, CT metadata/feature planning, and CT/WSI pairing-gate routing.

The output directory contains:

- `manifest.json`
- `project_status.json`
- `branches/<branch-id>/branch_status.json`
- `branches/<branch-id>/evidence/evidence_bundle.json`
- planned trace and artifact JSON files for each branch

Validate the generated package before collecting it:

```bash
python -m brainfusion_agents validate-project-package --package-dir outputs/cloud-job/project-dry-run
```

The validator checks that all listed package files exist, every branch has an evidence bundle, no data is marked downloaded, downloads remain blocked, and no dry-run trace claims support for the main conclusion or extension experiment.

## Container Entry

Build and run:

```bash
docker build -t brainfusion-agents:dry-run .
docker run --rm brainfusion-agents:dry-run
```

The default container command runs the source tree directly with `python -m brainfusion_agents cloud-job` and writes `outputs/cloud-job` inside the container. On a cloud platform, mount or collect that directory as the job artifact.

## Data Boundary

Keep real data outside this repository. In the current phase, registry and manifest files must contain source IDs, source URLs, access status, QC state, and audit evidence only.

Forbidden fields in committed metadata include:

- `local_path`
- `download_path`
- local DICOM, slide, patch, feature, or embedding paths

When data access is later approved on a cloud platform, add ingestion code behind an explicit new phase and keep generated outputs under ignored directories such as `outputs/` or platform-managed storage.
