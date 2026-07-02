---
id: BF-003
title: Design PET/MR MVP workflow
status: ready-for-agent
type: AFK
blocked_by: ["BF-001", "BF-002"]
stage: pet-mr-mainline
modality: PET/MR
---

# Design PET/MR MVP workflow

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Specify the PET/MR mainline workflow using ADNI for development and OASIS-3 for external validation. The workflow must cover PET-only, MR-only, PET/MR fusion, and the multi-agent evidence trail around QC and failure recovery.

## Acceptance criteria

- [ ] PET-only, MR-only, and PET/MR fusion baselines are defined.
- [ ] ADNI subject/session alignment requirements are listed.
- [ ] OASIS-3 validation handoff is defined separately from ADNI development.
- [ ] PET and MR QC gates are defined before fusion.
- [ ] The multi-agent contribution is framed as workflow robustness, not model replacement.
- [ ] Required trace fields are listed for every PET/MR run.

## Blocked by

- BF-001
- BF-002

## Comments

