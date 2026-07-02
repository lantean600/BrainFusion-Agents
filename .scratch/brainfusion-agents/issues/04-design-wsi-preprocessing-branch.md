---
id: BF-004
title: Design WSI preprocessing branch
status: ready-for-agent
type: AFK
blocked_by: ["BF-001", "BF-002"]
stage: wsi-preprocessing
modality: WSI
---

# Design WSI preprocessing branch

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Specify the pathology WSI preprocessing branch for TCGA/GDC scale data and CAMELYON/PANDA/IGNITE benchmark data. This branch prepares WSI evidence for future use but does not assume pairing with PET/MR or CT.

## Acceptance criteria

- [ ] Tissue detection, artifact filtering, stain normalization, patch extraction, and embedding extraction are defined as branch tasks.
- [ ] TCGA/GDC is documented as the scale dataset source.
- [ ] CAMELYON/PANDA/IGNITE are documented as labeled preprocessing or QC benchmarks.
- [ ] UNI or another pathology foundation model is treated as an embedding extractor candidate.
- [ ] WSI output manifest requirements are defined.
- [ ] The branch is explicitly not a PET/MR or CT fusion workflow by default.

## Blocked by

- BF-001
- BF-002

## Comments

