# Agent Trace Specification

Agent traces are structured records that make workflow decisions auditable. A trace is not just a runtime log; it is evidence for why a case, modality, baseline, QC decision, or conclusion was accepted.

## Minimal Trace Fields

```yaml
trace_id: string
workflow_id: string
agent_name: string
agent_version: string
dataset_id: string
subject_id: string
session_id: string | null
input_modalities: list[string]
task: string
model_name: string | null
model_version: string | null
parameters: map
qc:
  status: pass | warn | fail | needs-human-review
  checks: list[string]
  reasons: list[string]
failure:
  failed: boolean
  category: data-missing | qc-failed | model-error | pairing-unverified | access-blocked | none
  message: string | null
human_review:
  required: boolean
  completed: boolean
  reviewer: string | null
evidence:
  artifacts: list[string]
  metrics: map
  source_records: list[string]
conclusion_support:
  supports_main_conclusion: boolean
  supports_extension_experiment: boolean
  limitations: list[string]
created_at: string
```

## QC Status Semantics

- `pass`: downstream workflow may proceed.
- `warn`: downstream workflow may proceed, but warning must appear in the evidence bundle.
- `fail`: downstream workflow must stop or use an explicitly allowed fallback.
- `needs-human-review`: downstream workflow waits for a human decision.

## Failure Categories

- `data-missing`: required modality or metadata is absent.
- `qc-failed`: quality-control gate failed.
- `model-error`: baseline or model invocation failed.
- `pairing-unverified`: CT/WSI pairing is not proven.
- `access-blocked`: dataset access is unavailable or not approved.
- `none`: no failure.

## Evidence Rules

- A trace may support the PET/MR main conclusion only when the route is PET/MR mainline and required QC gates pass.
- A CT-pathology trace may support a formal extension only when the pairing gate passes.
- Missing modalities must be represented explicitly; absence is not a negative result.
- Human review must be recorded before a `needs-human-review` trace can be used in conclusions.

