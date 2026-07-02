# PET/MR MVP Workflow

The PET/MR mainline is the first publishable version of BrainFusion-Agents. It uses ADNI as the primary development dataset and OASIS-3 as the external validation dataset.

## Research Claim

The MVP claim is not that agents outperform fusion models directly. The claim is that a multi-agent workflow improves PET/MR experiment reliability by making modality availability, preprocessing assumptions, QC gates, failure recovery, and evidence traces explicit.

## Required Comparisons

| Comparison | Purpose | Required output |
| --- | --- | --- |
| PET-only baseline | Measures PET evidence without MR contribution. | Metrics, QC summary, trace bundle. |
| MR-only baseline | Measures MR evidence without PET contribution. | Metrics, QC summary, trace bundle. |
| PET/MR fusion baseline | Measures fused multimodal model behavior. | Metrics, fusion report, trace bundle. |
| Multi-agent PET/MR workflow | Measures workflow robustness around the baselines. | Failure recovery report, evidence coverage, QC audit. |

## Dataset Handling

ADNI:

- Use as the primary development dataset.
- Track subject, visit/session, PET tracer, MR sequence, diagnosis label, clinical timepoint, and QC status.
- Align PET and MR at subject/session or nearest clinically justified visit level.
- Record any excluded cases and exclusion reasons.

OASIS-3:

- Use only after the ADNI workflow is stable.
- Treat as external validation, not as a tuning source.
- Record differences in tracer availability, MR sessions, and label definitions.

## Agent Flow

1. Dataset Registry Agent confirms access status and modality inventory.
2. Central Dispatcher selects `PET/MR mainline` for cases with usable PET and MR.
3. PET Agent validates tracer, acquisition metadata, preprocessing assumptions, and PET QC.
4. MR Agent validates sequence availability, structural image usability, preprocessing assumptions, and MR QC.
5. PET/MR Fusion Agent runs PET-only, MR-only, and PET/MR comparisons.
6. Evidence Agent collects traces, metrics, warnings, exclusions, and artifacts.

## QC Gates

- PET presence and tracer eligibility.
- MR presence and sequence eligibility.
- Subject/session alignment.
- Preprocessing compatibility.
- Label availability.
- Model input completeness.
- Evidence trace completeness.

Any failed gate must either stop the case or route it to a documented fallback. Silent dropping is not allowed.

## Deliverables

- ADNI case selection manifest.
- OASIS-3 validation manifest.
- PET-only, MR-only, PET/MR comparison report.
- QC and exclusion report.
- Agent trace bundle.
- Short publication-facing statement separating model results from workflow reliability results.

