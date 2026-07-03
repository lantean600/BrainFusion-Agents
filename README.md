# BrainFusion-Agents

BrainFusion-Agents is a research project workspace for a multi-agent, multimodal medical AI system. The project uses a staged public-dataset strategy instead of assuming one public cohort can cover paired brain PET, brain MR, CT, and pathology WSI for the same patients.

The MVP is the brain PET/MR mainline: ADNI is the primary development dataset, OASIS-3 is the external validation dataset, and the system evaluates whether agents improve quality control, failure recovery, evidence tracking, and workflow robustness around PET/MR fusion.

## Project Shape

- `AGENTS.md`: repo-level instructions for Codex and other engineering agents.
- `CONTEXT.md`: domain glossary. Keep it implementation-free.
- `docs/agents/`: Matt Pocock skills configuration for local Markdown issues, triage labels, and domain docs.
- `docs/adr/`: architectural decisions that future agents should respect.
- `docs/cloud-run.md`: cloud compute dry-run installation and container instructions.
- `docs/design/`: research design, dataset strategy, agent architecture, roadmap, and trace contract.
- `examples/manifests/`: no-download sample manifests for cloud preflight checks.
- `.scratch/brainfusion-agents/PRD.md`: product/research requirements synthesized from the project plan.
- `.scratch/brainfusion-agents/issues/`: tracer-bullet issues ready for agent execution.

Key design entrypoints:

- `docs/design/public-dataset-strategy.md`
- `docs/design/implementation-kernel.md`
- `docs/design/pet-mr-mvp-workflow.md`
- `docs/design/wsi-preprocessing-branch.md`
- `docs/design/ct-agent-prototype.md`
- `docs/design/ct-pathology-pairing-gate.md`
- `docs/design/system-architecture.md`
- `docs/design/agent-trace-spec.md`

## Current Decisions

- Track work locally in Markdown, not GitHub Issues.
- Use `AGENTS.md` as the agent instruction entrypoint.
- Use one global domain context: root `CONTEXT.md` plus `docs/adr/`.
- Make PET/MR the publishable MVP.
- Treat WSI and CT as staged branches.
- Treat CT-pathology fusion as a gated extension that requires confirmed patient-level pairing.

## First Execution Path

Start with `.scratch/brainfusion-agents/issues/01-initialize-project-workspace.md`, then proceed through the numbered issues in dependency order.

## Implementation Kernel

The current implementation is a standard-library Python package under `src/brainfusion_agents/`.

It provides:

- dataset registry loading from `data/dataset_registry.json`;
- dataset registry auditing for no-download and strategy invariants;
- PET/MR case selection manifest templates and validation;
- CT-pathology pairing audit manifest templates and validation;
- WSI preprocessing manifest templates and validation;
- CT prototype manifest templates and validation;
- PET/MR metadata readiness reporting from registry + manifest;
- WSI and CT metadata readiness reporting from registry + branch manifests;
- workflow routing for PET/MR, PET-only, MR-only, WSI, CT, and CT+WSI cases;
- executable workflow planning from dataset IDs, including QC gates and expected artifacts;
- dry-run evidence bundle generation for planned artifacts and non-claim-supporting traces;
- local materialization of dry-run evidence packages;
- executable preprocessing/fusion pipeline dry runs for PET/MR, WSI, CT, and CT/WSI pairing;
- synthetic no-download runtime demo for PET/MR fusion, CT preprocessing, and WSI preprocessing calculations;
- tumor-first dataset download planning and automatic public smoke-dataset download;
- CT-pathology pairing gate evaluation;
- agent trace validation for main-conclusion and extension-experiment claims;
- project-level cloud dry-run status reporting;
- one-command cloud job materialization for project evidence, pipeline reports, and summary output;
- CLI access through `python -m brainfusion_agents`.

No dataset download is performed. The registry keeps source links and access status only.

The CLI reads `data/dataset_registry.json` when run from the repository root. If the package is installed and launched from another working directory, it falls back to the bundled registry copy inside `brainfusion_agents`.

## Cloud Runnable Dry Run

The current complete runnable version is a cloud-ready tumor-first smoke job. It can be installed on a cloud compute platform and used to download public tumor smoke datasets, validate registry rules, route workflows, materialize manifests, run pairing gates, generate pipeline task plans, and collect planned evidence artifacts before restricted TCIA/GDC/ADNI-style access is approved.

```bash
python -m pip install .
brainfusion-agents cloud-job --output-dir outputs/cloud-job
```

`cloud-job` is the recommended cloud platform entrypoint. By default it automatically downloads public tumor smoke datasets from the bundled tumor download plan:

- `medmnist-breastmnist`: breast ultrasound tumor classification smoke data.
- `medmnist-nodulemnist3d`: lung nodule CT malignancy smoke data.
- `medmnist-pathmnist`: colorectal cancer histology patch smoke data.

It writes:

- `outputs/cloud-job/job_summary.json`
- `outputs/cloud-job/downloads/`
- `outputs/cloud-job/project-dry-run/`
- `outputs/cloud-job/pipeline-run/`
- `outputs/cloud-job/synthetic-runtime/`

The synthetic runtime directory contains computed smoke-test outputs for PET/MR fusion, CT feature extraction, and WSI tile/embedding preprocessing. It uses generated arrays only; the downloaded MedMNIST tumor files are collected for cloud data availability checks and later ingestion wiring.

For CI or offline checks, disable downloads explicitly:

```bash
brainfusion-agents cloud-job --output-dir outputs/cloud-job --download-policy off
```

Formal TCIA/IDC/GDC tumor cohorts remain supported through manifests, IDC tools, GDC manifests, and tokens. The project does not pretend those restricted or very large cohorts can be downloaded without the required access setup.

Run the included no-download samples:

```bash
brainfusion-agents project-status \
  --pet-mr-manifest examples/manifests/adni-case-selection.sample.json \
  --wsi-manifest examples/manifests/tcga-wsi-preprocessing.sample.json \
  --ct-manifest examples/manifests/lidc-ct-prototype.sample.json \
  --pairing-manifest examples/manifests/ct-wsi-pairing-audit.sample.json
```

The container entrypoint runs the same sample status check:

```bash
docker build -t brainfusion-agents:dry-run .
docker run --rm brainfusion-agents:dry-run
```

The default container command runs the source tree directly with `python -m brainfusion_agents cloud-job` and writes project, pipeline, and summary outputs to `outputs/cloud-job`.

See `docs/cloud-run.md` for the release boundary and data rules.

## Commands

Run tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

List PET datasets:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents datasets --modality PET
```

Audit the dataset registry:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents audit-registry
```

Build the project-level cloud dry-run status report:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents project-status
```

Run the full cloud job:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents cloud-job --output-dir outputs/cloud-job
```

Write the tumor download plan without network access:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents download-data --output-dir outputs/tumor-downloads --dataset-ids medmnist-breastmnist
```

Execute the public tumor smoke downloads:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents download-data --output-dir outputs/tumor-downloads --execute
```

Write a project-level dry-run evidence package:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents cloud-run --output-dir outputs/project-dry-run
```

Run the preprocessing and fusion pipeline:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents run-pipeline --output-dir outputs/pipeline-run
```

This writes `pipeline_report.json` plus task-level artifacts for PET/MR fusion, WSI preprocessing, CT preprocessing, and CT/WSI pairing audit.

Run the synthetic no-download runtime demo:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents synthetic-demo --output-dir outputs/synthetic-runtime
```

This writes computed PET/MR, CT, and WSI smoke-test JSON files using generated data only.

Validate a generated project dry-run package:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-project-package --package-dir outputs/project-dry-run
```

Print a PET/MR case selection manifest template:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents manifest-template
```

Validate a PET/MR case selection manifest:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-manifest --manifest manifests/adni-case-selection.json
```

Build a PET/MR metadata readiness report:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents pet-mr-readiness --dataset-ids adni oasis-3 --manifest manifests/adni-case-selection.json
```

Print a CT-pathology pairing audit manifest template:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents pairing-manifest-template
```

Validate a CT-pathology pairing audit manifest:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-pairing-manifest --manifest manifests/ct-wsi-pairing-audit.json
```

Print a WSI preprocessing manifest template:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents wsi-manifest-template
```

Validate a WSI preprocessing manifest:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-wsi-manifest --manifest manifests/tcga-wsi-preprocessing.json
```

Build a WSI metadata readiness report:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents wsi-readiness --dataset-ids tcga-gdc-wsi camelyon --manifest manifests/tcga-wsi-preprocessing.json
```

Print a CT prototype manifest template:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents ct-manifest-template
```

Validate a CT prototype manifest:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-ct-manifest --manifest manifests/lidc-ct-prototype.json
```

Build a CT metadata readiness report:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents ct-readiness --dataset-ids lidc-idri nsclc-radiomics --manifest manifests/lidc-ct-prototype.json
```

Route a PET/MR case:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents route --modalities PET MR
```

Build the PET/MR workflow plan from registry datasets:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents plan-datasets --dataset-ids adni oasis-3
```

Generate a dry-run evidence bundle:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents dry-run-evidence --dataset-ids adni oasis-3
```

Write a dry-run evidence package to a local directory:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents materialize-dry-run --dataset-ids adni oasis-3 --output-dir outputs/pet-mr-dry-run
```

Check that unpaired CT+WSI cannot claim fusion:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents pairing-gate --sources tcia tcga-gdc
```
