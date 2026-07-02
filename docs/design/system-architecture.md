# Multi-agent System Architecture

BrainFusion-Agents is a workflow system around multimodal medical AI. The agents do not replace fusion models; they make data availability, preprocessing, quality control, failure recovery, and evidence tracking explicit.

## Core Agents

| Agent | Responsibility | Output |
| --- | --- | --- |
| Dataset Registry Agent | Tracks datasets, access status, modalities, pairing evidence, and allowed tasks. | Dataset records and eligibility decisions. |
| Central Dispatcher Agent | Selects the workflow path based on available modalities and pairing gates. | Workflow route and required agents. |
| PET Agent | Handles PET availability, preprocessing assumptions, tracer metadata, QC, and PET baseline input. | PET features, QC result, trace. |
| MR Agent | Handles MR availability, preprocessing assumptions, structural imaging QC, and MR baseline input. | MR features, QC result, trace. |
| PET/MR Fusion Agent | Runs or coordinates PET-only, MR-only, and PET/MR fusion baselines. | Fusion result, comparison report, trace. |
| WSI Agent | Runs WSI preprocessing design: tissue detection, artifact filtering, stain normalization, patch extraction, embeddings. | Patch/embedding manifest, QC result, trace. |
| CT Agent | Runs CT prototype design: CT ingestion, lesion/nodule QC, segmentation/classification/radiomics baseline. | CT features, QC result, trace. |
| Pairing Gate Agent | Audits whether CT and WSI samples are patient-level or lesion-level paired. | Pairing verdict and evidence. |
| Evidence Agent | Collects traces and artifacts into an evidence trail for experiment claims. | Evidence bundle and audit summary. |

## Routing Rules

| Data available | Route | Claim level |
| --- | --- | --- |
| PET + MR | PET/MR mainline workflow | Eligible for MVP main conclusion after validation. |
| PET only | PET-only baseline workflow | Baseline evidence only. |
| MR only | MR-only baseline workflow | Baseline evidence only. |
| WSI only | WSI preprocessing branch | Extension/preprocessing evidence. |
| CT only | CT branch | Extension/prototype evidence. |
| CT + WSI with verified pairing | CT-pathology fusion workflow | Formal extension experiment. |
| CT + WSI without verified pairing | Separate CT and WSI workflows plus pairing audit | No fusion claim. |

## Workflow Contract

Each workflow must produce:

- input dataset record;
- modality availability decision;
- preprocessing assumptions;
- QC gate result;
- model or baseline invocation record;
- failure or warning state;
- human review state;
- evidence trail supporting any conclusion.

## MVP Flow

1. Dataset Registry Agent confirms ADNI/OASIS-3 access and modality inventory.
2. Central Dispatcher routes PET+MR cases to PET/MR mainline.
3. PET Agent and MR Agent produce modality-specific QC and features.
4. PET/MR Fusion Agent compares PET-only, MR-only, and PET/MR fusion.
5. Evidence Agent creates a trace bundle for workflow robustness and model comparison.
6. OASIS-3 is used as external validation after ADNI development is stable.

