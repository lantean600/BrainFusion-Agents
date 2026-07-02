---
id: BF-006
title: Define CT-pathology pairing gate
status: ready-for-agent
type: AFK
blocked_by: ["BF-002", "BF-004", "BF-005"]
stage: ct-pathology-extension
modality: CT+WSI
---

# Define CT-pathology pairing gate

Status: ready-for-agent

## Parent

`.scratch/brainfusion-agents/PRD.md`

## What to build

Define the gate that determines whether CT and WSI data can support formal CT-pathology fusion. The gate must distinguish patient-level pairing, lesion-level pairing, dataset-level co-availability, and unpaired multimodal resources.

## Acceptance criteria

- [ ] Patient-level pairing evidence requirements are defined.
- [ ] Lesion-level pairing evidence requirements are defined.
- [ ] Dataset-level co-availability is explicitly insufficient for fusion claims.
- [ ] CT-pathology is defined as cross-scale fusion, not pixel-level fusion.
- [ ] Missing-aware fusion is allowed only after pairing passes.
- [ ] Gate failure routes CT and WSI to separate branch workflows plus a pairing audit report.

## Blocked by

- BF-002
- BF-004
- BF-005

## Comments

