---
id: BF-002
title: Build public dataset matrix
status: ready-for-agent
type: AFK
blocked_by: ["BF-001"]
stage: dataset-strategy
modality: cross-modal
---

# Build public dataset matrix

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Create and maintain the public dataset strategy that classifies datasets by modality, project role, access constraints, pairing status, and whether they can support main conclusions or extension experiments.

## Acceptance criteria

- [ ] ADNI and OASIS-3 are documented as the PET/MR mainline datasets.
- [ ] OpenNeuro is documented only as a BIDS/MRI workflow supplement.
- [ ] LIDC-IDRI, NSCLC-Radiomics, and NLST are documented as CT branch candidates.
- [ ] TCGA/GDC, CAMELYON, PANDA, and IGNITE are documented as WSI branch candidates.
- [ ] CT + WSI datasets are marked as candidate paired cohorts only after an ID audit.
- [ ] Access status and data-use constraints are explicit for each dataset group.

## Blocked by

- BF-001

## Comments

