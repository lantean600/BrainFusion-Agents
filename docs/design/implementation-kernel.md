# Implementation Kernel

The implementation kernel turns the research design into testable workflow behavior without downloading medical datasets.

## Public Interfaces

| Interface | Module | Responsibility |
| --- | --- | --- |
| `audit_dataset_registry` | `brainfusion_agents.audit` | Check registry records against no-download, PET/MR mainline, source URL, and CT-pathology pairing invariants. |
| `CloudJobResult` / `run_cloud_job` | `brainfusion_agents.cloud_job` | Run the default cloud deliverable job and write project evidence, pipeline reports, validation results, and `job_summary.json`. |
| `ct_manifest_template` / `validate_ct_manifest` | `brainfusion_agents.ct_manifest` | Create and validate CT prototype manifests without local DICOM, CT, annotation, or feature paths. |
| `DatasetRegistry` | `brainfusion_agents.datasets` | Load and query dataset metadata links, access status, modality, branch, and pairing status. |
| `SyntheticRuntimeResult` / `run_synthetic_runtime_demo` | `brainfusion_agents.demo_runtime` | Run a generated-data PET/MR, CT, and WSI computation smoke test without downloading medical files. |
| `case_selection_manifest_template` / `validate_case_selection_manifest` | `brainfusion_agents.manifest` | Create and validate PET/MR case selection manifests without local image paths. |
| `pairing_manifest_template` / `validate_pairing_manifest` | `brainfusion_agents.pairing_manifest` | Create and validate CT-pathology pairing audit manifests, then evaluate the pairing gate. |
| `build_pet_mr_readiness_report` | `brainfusion_agents.readiness` | Combine registry audit, PET/MR workflow plan, and case selection manifest validation into a metadata readiness report. |
| `build_wsi_readiness_report` / `build_ct_readiness_report` | `brainfusion_agents.readiness` | Combine registry audit, branch workflow plan, and WSI/CT manifest validation into extension metadata readiness reports. |
| `wsi_manifest_template` / `validate_wsi_manifest` | `brainfusion_agents.wsi_manifest` | Create and validate WSI preprocessing manifests without local slide, patch, or embedding paths. |
| `WorkflowRequest` / `route_workflow` | `brainfusion_agents.workflow` | Route modality availability into PET/MR mainline, baselines, WSI branch, CT branch, or CT+WSI audit/fusion. |
| `WorkflowPlan` / `build_workflow_plan` | `brainfusion_agents.plans` | Build an executable plan from dataset IDs, including route, QC gates, expected artifacts, and trace requirements. |
| `DryRunEvidenceBundle` / `build_dry_run_evidence_bundle` | `brainfusion_agents.evidence` | Generate planned artifacts and dry-run traces without downloading or inspecting datasets. |
| `MaterializedEvidencePackage` / `materialize_dry_run_evidence_bundle` | `brainfusion_agents.materialize` | Write a dry-run package containing `manifest.json`, `evidence_bundle.json`, trace files, and planned artifact stubs. |
| `PairingEvidence` / `evaluate_pairing_gate` | `brainfusion_agents.pairing` | Decide whether CT+WSI evidence passes patient-level or lesion-level pairing requirements. |
| `MaterializedProjectDryRunPackage` / `materialize_project_dry_run` | `brainfusion_agents.project_run` | Write a project-level dry-run package with status, branch evidence bundles, trace files, and artifact stubs. |
| `ProjectPackageValidationResult` / `validate_project_package` | `brainfusion_agents.package_validation` | Validate a materialized project dry-run package before collecting it as a cloud job artifact. |
| `PipelineRunResult` / `materialize_pipeline_run` | `brainfusion_agents.pipeline` | Run a no-download preprocessing/fusion pipeline and write task-level PET/MR, WSI, CT, and CT/WSI artifacts. |
| `ProjectStatusReport` / `build_project_status_report` | `brainfusion_agents.project_status` | Aggregate registry audit, default workflow plans, optional branch manifests, and pairing audit state into a cloud dry-run status report. |
| `AgentTrace` / `validate_trace` | `brainfusion_agents.trace` | Validate whether a trace can support the PET/MR main conclusion or an extension experiment. |
| CLI | `brainfusion_agents.cli` | Expose registry, routing, planning, and pairing gate checks from the command line. |

## Dataset Metadata

Dataset metadata lives in `data/dataset_registry.json`. Records keep:

- dataset ID and display name;
- modalities;
- branch and role;
- access status;
- source URLs;
- pairing status;
- notes.

Records must not include local downloaded paths unless the project explicitly moves into a data-ingestion phase after human approval.

## Registry Audit

`audit_dataset_registry` verifies:

- ADNI exists and remains `primary-development`;
- OASIS-3 exists and remains `external-validation`;
- no dataset has `access_status=downloaded` in the current phase;
- source URLs are HTTP(S) links;
- CT+WSI candidate entries remain `unverified` until pairing gate evidence is recorded;
- PET/MR mainline entries declare exactly PET and MR modalities.

Command:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents audit-registry
```

## Routing Behavior

- `PET + MR` routes to `pet_mr_mainline` and is eligible for the main conclusion after validation.
- `PET` routes to `pet_only_baseline`.
- `MR` routes to `mr_only_baseline`.
- `WSI` routes to `wsi_preprocessing`.
- `CT` routes to `ct_branch`.
- `CT + WSI` routes to `ct_pathology_fusion` only when pairing is verified at `patient-level` or `lesion-level`.
- Unverified `CT + WSI` routes to `ct_wsi_separate_with_pairing_audit`.

## PET/MR Case Selection Manifest

`case_selection_manifest_template` provides a JSON template for ADNI/OASIS-3 case selection. Records keep source identifiers and QC state only; local image paths are forbidden in this phase.

Required record fields:

- `subject_id`
- `session_id`
- `diagnosis_label`
- `clinical_timepoint`
- `pet_available`
- `mr_available`
- `pet_tracer`
- `mr_sequence`
- `pet_qc_status`
- `mr_qc_status`
- `alignment_status`
- `source_record`

Commands:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents manifest-template
python -m brainfusion_agents validate-manifest --manifest manifests/adni-case-selection.json
```

## PET/MR Readiness Report

`build_pet_mr_readiness_report` checks whether the PET/MR mainline metadata is ready for dry-run workflow planning:

- registry audit passes;
- selected datasets include `adni` and `oasis-3`;
- route is `pet_mr_mainline`;
- case selection manifest validates;
- manifest contains at least one record;
- manifest `dataset_id` is included in the selected dataset IDs.

The report always sets `dry_run_only=true` and `can_support_main_conclusion=false` in the current no-download phase.

Command:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents pet-mr-readiness --dataset-ids adni oasis-3 --manifest manifests/adni-case-selection.json
```

## CT-pathology Pairing Manifest

`pairing_manifest_template` provides a JSON template for auditing whether CT and WSI records can support cross-scale fusion. It reuses the pairing gate rules: patient-level or lesion-level pairing requires source datasets, identifier fields, paired patient count, timing assumption, and endpoint availability.

Commands:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents pairing-manifest-template
python -m brainfusion_agents validate-pairing-manifest --manifest manifests/ct-wsi-pairing-audit.json
```

Local CT/WSI paths are forbidden in this phase; the manifest keeps source identifiers and audit evidence only.

## WSI Preprocessing Manifest

`wsi_manifest_template` provides a JSON template for TCGA/GDC, CAMELYON, PANDA, IGNITE, or other WSI preprocessing metadata. Records track slide IDs, source records, tissue/artifact/stain/patch/embedding status, patch count, QC status, and trace ID.

Commands:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents wsi-manifest-template
python -m brainfusion_agents validate-wsi-manifest --manifest manifests/tcga-wsi-preprocessing.json
```

Local slide, patch, and embedding paths are forbidden in this phase. The manifest is for preprocessing readiness and trace planning only.

WSI readiness command:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents wsi-readiness --dataset-ids tcga-gdc-wsi camelyon --manifest manifests/tcga-wsi-preprocessing.json
```

The report sets `dry_run_only=true` and `can_support_extension_experiment=false` in the current no-download phase.

## CT Prototype Manifest

`ct_manifest_template` provides a JSON template for LIDC-IDRI, NSCLC-Radiomics, NLST, or other CT prototype metadata. Records track case/study/series identifiers, CT protocol, annotation availability, baseline type, feature manifest status, QC status, and trace ID.

Commands:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents ct-manifest-template
python -m brainfusion_agents validate-ct-manifest --manifest manifests/lidc-ct-prototype.json
```

Local DICOM, CT, annotation, and feature paths are forbidden in this phase. The manifest is for CT branch readiness and trace planning only.

CT readiness command:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents ct-readiness --dataset-ids lidc-idri nsclc-radiomics --manifest manifests/lidc-ct-prototype.json
```

The report sets `dry_run_only=true` and `can_support_extension_experiment=false` in the current no-download phase.

## Project Status

`build_project_status_report` is the cloud preflight entrypoint. It aggregates:

- registry audit status;
- PET/MR, WSI, CT, and CT-pathology pairing branch plans;
- optional manifest readiness for each branch;
- no-download enforcement;
- explicit blockers for metadata readiness and claim support.

Command without manifests:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents project-status
```

Command with included no-download samples:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents project-status --pet-mr-manifest examples/manifests/adni-case-selection.sample.json --wsi-manifest examples/manifests/tcga-wsi-preprocessing.sample.json --ct-manifest examples/manifests/lidc-ct-prototype.sample.json --pairing-manifest examples/manifests/ct-wsi-pairing-audit.sample.json
```

The report can be `cloud_runnable=true` while still listing metadata blockers. That means the software can run on a cloud platform, but formal experiments remain blocked until valid manifests and approved data access exist.

## Workflow Plans

`build_workflow_plan` adds implementation-facing detail to a route:

- dataset IDs and names;
- available modalities;
- required QC gates;
- expected artifacts;
- trace requirements;
- `downloads_blocked=True`.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents plan-datasets --dataset-ids adni oasis-3
```

This returns a PET/MR mainline plan with subject/session alignment, PET/MR QC gates, baseline reports, validation manifest, and an agent trace bundle.

## Trace Rules

- Main-conclusion traces must come from `pet_mr_mainline`, include PET and MR, pass QC, have no failure, and include source records.
- CT-pathology extension traces require `pairing_gate_status=pass` and `pairing_level` of `patient-level` or `lesion-level`.
- A trace requiring human review cannot support a conclusion until review is completed.
- Missing modalities or failed QC must be represented explicitly, not silently dropped.

## Dry-run Evidence

`build_dry_run_evidence_bundle` converts a workflow plan into a non-claim-supporting evidence scaffold:

- all expected artifacts are marked `planned`;
- traces are generated for the route's required agents;
- `downloads_blocked=True` and `data_downloaded=False`;
- no trace supports the main conclusion or an extension experiment;
- unpaired CT+WSI dry runs include `pairing_audit_report` and exclude `ct_wsi_fusion_report`.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents dry-run-evidence --dataset-ids adni oasis-3
```

The output is safe to use before data access approval because it only references registry dataset IDs and planned artifacts.

## Materialized Packages

`materialize_dry_run_evidence_bundle` writes a local package with:

- `manifest.json`;
- `evidence_bundle.json`;
- `traces/*.json`;
- `artifacts/*.json` planned artifact stubs.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents materialize-dry-run --dataset-ids adni oasis-3 --output-dir outputs/pet-mr-dry-run
```

The package is still a dry run: every artifact stub has `status=planned`, `data_downloaded=false`, and `downloads_blocked=true`.

## Project Dry-run Package

`materialize_project_dry_run` writes a cloud job artifact for all default branches. It includes:

- root `manifest.json`;
- root `project_status.json`;
- branch status files;
- branch-level evidence bundles;
- trace files and planned artifact stubs.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents materialize-project-dry-run --output-dir outputs/project-dry-run --pet-mr-manifest examples/manifests/adni-case-selection.sample.json --wsi-manifest examples/manifests/tcga-wsi-preprocessing.sample.json --ct-manifest examples/manifests/lidc-ct-prototype.sample.json --pairing-manifest examples/manifests/ct-wsi-pairing-audit.sample.json
```

This is the preferred cloud preflight artifact because it gives the scheduler one output directory to persist.

Validate the package:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents validate-project-package --package-dir outputs/project-dry-run
```

The validator checks root manifest/status invariants, branch evidence bundles, listed file existence, no-download flags, and absence of dry-run claim support.

## Preprocessing And Fusion Pipeline

`materialize_pipeline_run` is the executable dry-run pipeline for the deliverable project. It writes task-level artifacts for:

- PET/MR QC, subject/session alignment, and fusion planning;
- WSI slide QC, tissue detection, artifact filtering, patch extraction, and embedding planning;
- CT series QC, metadata QC, annotation readiness, feature extraction, and baseline planning;
- CT/WSI pairing-gate routing and fusion blocker reporting.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents run-pipeline --output-dir outputs/pipeline-run
```

The pipeline remains metadata-only: it uses registry links and manifests, writes source-ID based plans, and keeps `data_downloaded=false`.

## Cloud Job

`run_cloud_job` is the cloud platform entrypoint for the current deliverable. It runs both project materialization and pipeline materialization, validates the project package, and writes a root `job_summary.json`.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents cloud-job --output-dir outputs/cloud-job
```

The output layout is:

- `job_summary.json`
- `project-dry-run/manifest.json`
- `project-dry-run/project_status.json`
- `pipeline-run/manifest.json`
- `pipeline-run/pipeline_report.json`
- `synthetic-runtime/demo_summary.json`

This is still a no-download job. A successful run proves that the repository can execute on cloud compute, produce collectable planning artifacts, and run a small generated-data computation path; it does not claim trained performance or paired patient-level CT/WSI fusion.

## Synthetic Runtime Demo

`run_synthetic_runtime_demo` generates small in-memory arrays and computes:

- PET z-score preprocessing, MR min/max preprocessing, and PET/MR fused feature summaries;
- CT z-score preprocessing and radiomics-like high-density features;
- WSI tile tissue filtering, artifact filtering, stain statistics, and an 8-value synthetic embedding.

Example:

```powershell
$env:PYTHONPATH='src'
python -m brainfusion_agents synthetic-demo --output-dir outputs/synthetic-runtime
```

The outputs are useful for cloud smoke tests and artifact collection. They remain explicitly synthetic and cannot support clinical or publication claims.

## Verification

The test suite uses `unittest` and exercises public behavior:

- dataset registry queries;
- workflow routing;
- pairing gate decisions;
- trace validation;
- CLI subprocess calls.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```
