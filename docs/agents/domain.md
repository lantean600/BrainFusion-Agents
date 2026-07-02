# Domain Docs

How engineering skills should consume this repo's domain documentation.

## Before exploring, read these

- `CONTEXT.md` at the repo root.
- ADRs in `docs/adr/` that touch the area being changed.
- Relevant design docs in `docs/design/` when working on datasets, workflows, traces, or experiments.

## Layout

This is a single-context repo:

```text
/
  CONTEXT.md
  docs/
    adr/
    design/
```

Do not create `CONTEXT-MAP.md` unless the project becomes a true monorepo with independent bounded contexts.

## Use the glossary's vocabulary

When output names a domain concept, use the term as defined in `CONTEXT.md`. If the concept is missing, add or propose a glossary term instead of inventing synonyms across issues and docs.

## Flag ADR conflicts

If a proposed change contradicts an ADR, surface it explicitly and either revise the change or add a new ADR that supersedes the old decision.

