---
id: BF-005
title: Design CT agent prototype
status: ready-for-agent
type: AFK
blocked_by: ["BF-001", "BF-002"]
stage: ct-prototype
modality: CT
---

# Design CT agent prototype

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Specify the CT branch prototype using LIDC-IDRI first and NSCLC-Radiomics or NLST for cancer CT expansion. The branch should support CT quality control, lesion or nodule workflows, and CT feature outputs without requiring pathology pairing.

## Acceptance criteria

- [ ] LIDC-IDRI is defined as the initial CT prototype dataset.
- [ ] NSCLC-Radiomics and NLST are defined as cancer CT expansion candidates.
- [ ] CT QC and baseline outputs are defined at a workflow level.
- [ ] Segmentation, classification, and radiomics are treated as baseline options.
- [ ] CT outputs can later feed CT-pathology fusion only through a pairing gate.

## Blocked by

- BF-001
- BF-002

## Comments

