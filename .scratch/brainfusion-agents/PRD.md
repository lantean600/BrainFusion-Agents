# BrainFusion-Agents Research PRD

Status: ready-for-agent

## Problem Statement

The project needs a credible, executable research design for a multi-agent multimodal medical AI system. The original four-modality ambition is not realistic as one public, fully paired cohort because brain PET, brain MR, CT, and pathology WSI are usually distributed across different studies, diseases, and access regimes.

The project therefore needs a staged public-dataset strategy, a precise vocabulary, auditable workflow traces, and an issue backlog that lets agents build the research project incrementally without overclaiming CT-pathology fusion or weakening the PET/MR mainline.

## Solution

Build BrainFusion-Agents as a local Markdown driven research workspace. Use ADNI and OASIS-3 for the PET/MR mainline, TCGA/GDC and pathology benchmarks for WSI preprocessing, TCIA/IDC CT datasets for CT prototyping, and a strict pairing gate before any CT-pathology fusion experiment.

The system design will center on specialized agents for dataset registry, dispatching, PET, MR, WSI, CT, pairing gates, QC, and evidence trails. The first publishable MVP is the PET/MR mainline; WSI and CT branches mature as extension experiments.

## User Stories

1. As a researcher, I want a public-dataset strategy that does not require one impossible four-modality cohort, so that the project can proceed credibly.
2. As a researcher, I want ADNI identified as the PET/MR primary dataset, so that the MVP has a strong development source.
3. As a researcher, I want OASIS-3 identified as an external validation dataset, so that PET/MR results are not limited to one cohort.
4. As a researcher, I want PET-only, MR-only, and PET/MR baselines, so that fusion benefit can be compared against unimodal evidence.
5. As a researcher, I want the multi-agent contribution framed as QC, recovery, evidence tracking, and workflow robustness, so that the claim does not compete incorrectly with fusion models.
6. As a pathology researcher, I want a WSI preprocessing branch, so that TCGA/CAMELYON/PANDA/IGNITE work can progress without pretending it is paired with PET/MR.
7. As a CT researcher, I want a CT agent prototype using LIDC-IDRI and NSCLC CT collections, so that CT processing can mature independently.
8. As a multimodal researcher, I want CT-pathology fusion blocked by a pairing gate, so that the project does not claim unsupported patient-level fusion.
9. As an agent operator, I want each workflow to emit traces, so that every conclusion has evidence.
10. As an agent operator, I want local Markdown issues, so that work can be assigned and resumed without a remote issue tracker.
11. As a future implementer, I want glossary terms and ADRs, so that agents use consistent language and preserve important decisions.
12. As a reviewer, I want clear boundaries between main conclusions and extension experiments, so that publication claims are defensible.

## Implementation Decisions

- Use local Markdown as the issue tracker under `.scratch/brainfusion-agents/`.
- Use `AGENTS.md` as the repo-level instruction file.
- Use one global `CONTEXT.md` and `docs/adr/` layout.
- Treat PET/MR as the MVP mainline.
- Treat WSI preprocessing and CT processing as staged branches.
- Treat CT-pathology fusion as a gated extension requiring verified patient-level or lesion-level pairing.
- Define a minimal agent trace interface covering modality inputs, models, parameters, QC, failures, human review, and evidence.
- Maintain dataset records with modality, access, limits, role, and pairing status.

## Testing Decisions

- Tests should verify externally visible workflow behavior once code exists.
- Priority test targets are dataset routing, pairing gates, trace validation, QC failure handling, and missing-aware fusion behavior.
- Documentation acceptance checks should verify that every issue has a status, dependency relationship, and concrete acceptance criteria.
- No tests should assume access to controlled datasets unless access credentials and local paths are explicitly configured.

## Out of Scope

- Downloading ADNI, OASIS-3, TCGA/GDC, TCIA, IDC, CAMELYON, PANDA, or IGNITE data.
- Claiming a four-modality patient-paired public cohort exists.
- Implementing production training code before the project design and issue backlog are stable.
- Treating CT-pathology as pixel-level fusion.
- Making CT-pathology part of the main conclusion before pairing is verified.

## Further Notes

The initial value of this workspace is disciplined project shape: consistent terms, documented decisions, a public dataset matrix, agent contracts, and execution slices. Future implementation should follow the numbered issues and add code only when a slice has clear acceptance criteria.

