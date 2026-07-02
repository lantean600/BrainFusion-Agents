# BrainFusion-Agents Agent Instructions

This repository is a local Markdown driven research project workspace for BrainFusion-Agents.

## Agent skills

### Issue tracker

Issues and PRDs are tracked as local Markdown files under `.scratch/brainfusion-agents/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default mattpocock/skills five-role label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context project: read root `CONTEXT.md` and relevant ADRs in `docs/adr/` before changing design or implementation. See `docs/agents/domain.md`.

## Project Rules

- Preserve the project vocabulary in `CONTEXT.md`; add or refine terms before introducing competing names.
- Record durable tradeoff decisions as ADRs in `docs/adr/`.
- Do not claim CT-pathology fusion as a formal experiment until patient-level pairing is verified.
- Do not download controlled medical datasets or create access credentials without explicit human approval.
- Keep public data strategy separate from executable preprocessing code.
- Every agent-facing design change should update either the PRD, a design doc, or a local issue.

## Execution Rules

- Work from `.scratch/brainfusion-agents/issues/` in dependency order.
- Mark issue status by editing the `Status:` line and the `status` frontmatter field.
- Prefer tracer-bullet slices: each issue should produce a verifiable artifact or behavior.
- For future code, test through public interfaces and observable workflow behavior, not private implementation details.

