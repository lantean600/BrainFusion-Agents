---
id: BF-007
title: Specify central dispatch and trace contract
status: ready-for-agent
type: AFK
blocked_by: ["BF-003", "BF-004", "BF-005", "BF-006"]
stage: system-integration
modality: cross-modal
---

# Specify central dispatch and trace contract

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Specify the central dispatcher behavior and the agent trace contract that every modality branch must follow. This slice makes route selection, QC states, failure states, human review, and evidence support consistent across PET/MR, WSI, CT, and CT-pathology workflows.

## Acceptance criteria

- [ ] Routing rules exist for PET/MR, PET-only, MR-only, WSI-only, CT-only, paired CT+WSI, and unpaired CT+WSI.
- [ ] Minimal trace fields include input modality, model, parameters, QC result, failure state, human review, and evidence.
- [ ] QC statuses have pass, warn, fail, and needs-human-review semantics.
- [ ] Failure categories include missing data, QC failure, model error, unverified pairing, and access block.
- [ ] Evidence rules distinguish support for main conclusions from extension experiments.
- [ ] Missing modalities are represented explicitly in trace output.

## Blocked by

- BF-003
- BF-004
- BF-005
- BF-006

## Comments

