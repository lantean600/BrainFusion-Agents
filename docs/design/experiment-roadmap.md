# Experiment Roadmap

## Stage 1: PET/MR Mainline Validation

Goal: prove the multi-agent workflow improves reliability and auditability around PET/MR fusion, not that agents replace the fusion model.

Datasets:

- ADNI as primary development dataset.
- OASIS-3 as external validation dataset.

Experiments:

- PET-only baseline.
- MR-only baseline.
- PET/MR fusion baseline.
- PET/MR multi-agent workflow with QC, failure recovery, and evidence tracking.

Success criteria:

- Reproducible subject/session selection.
- Clear PET/MR preprocessing assumptions.
- Baseline comparison report.
- Trace coverage for every included subject/session.
- External validation result on OASIS-3.

## Stage 2: WSI Preprocessing Branch

Goal: establish a pathology agent that can prepare WSI data for downstream feature extraction and future fusion.

Datasets:

- TCGA/GDC WSI for scale.
- CAMELYON, PANDA, and IGNITE for labeled preprocessing or QC benchmarks.

Tasks:

- Tissue detection.
- Artifact filtering.
- Stain normalization.
- Patch extraction.
- WSI embedding extraction using a pathology foundation model such as UNI.

Success criteria:

- Patch and embedding manifest format.
- QC report for tissue coverage and artifact filtering.
- Benchmark-specific evaluation where labels exist.

## Stage 3: CT Branch and CT-pathology Extension

Goal: prototype CT processing and only extend to CT-pathology fusion after pairing is verified.

Datasets:

- LIDC-IDRI for CT agent prototype.
- NSCLC-Radiomics and NLST via TCIA/IDC for cancer CT expansion.
- TCGA/GDC or NSCLC WSI data for pathology branch candidates.

Experiments after pairing passes:

- CT-only baseline.
- WSI-only baseline.
- CT + WSI late fusion.
- CT + WSI intermediate fusion.
- Missing-aware CT/WSI fusion.

Success criteria:

- Pairing audit proves patient-level or lesion-level linkage.
- CT-pathology is described as cross-scale fusion.
- Missing modalities are explicitly represented.

## Stage 4: Integrated Multi-agent System

Goal: unify route selection, traces, QC gates, and evidence bundles across modality branches.

Dispatcher behavior:

- `PET/MR available` -> PET/MR fusion workflow.
- `WSI available` -> WSI preprocessing workflow.
- `CT + WSI available and paired` -> CT-pathology fusion workflow.
- `CT + WSI available but not paired` -> separate branch workflows plus pairing audit.

Success criteria:

- Every workflow path has trace output.
- Failed QC blocks unsupported conclusions.
- Human review decisions are recorded.
- Evidence bundles can reproduce why a conclusion was accepted, downgraded, or excluded.

## Recommended MVP

1. ADNI + OASIS-3 PET/MR workflow.
2. TCGA/CAMELYON/PANDA WSI preprocessing agent.
3. LIDC-IDRI/NSCLC-Radiomics CT agent prototype.
4. CT-pathology fusion only if paired samples are confirmed.

