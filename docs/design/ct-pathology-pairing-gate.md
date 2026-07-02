# CT-pathology Pairing Gate

The CT-pathology pairing gate decides whether CT and WSI data can support a formal cross-scale fusion experiment.

## Gate Principle

CT-pathology fusion requires verified patient-level or lesion-level pairing. Dataset-level co-availability, shared cancer type, or similar publication context is not enough.

## Pairing Levels

| Level | Meaning | Fusion eligibility |
| --- | --- | --- |
| Dataset-level co-availability | CT and WSI exist somewhere across related resources. | Not eligible. |
| Cancer-type alignment | CT and WSI share disease type, such as NSCLC. | Not eligible by itself. |
| Patient-level pairing | CT and WSI records map to the same patient/case identifier. | Eligible for patient-level fusion. |
| Lesion-level pairing | CT lesion/tumor and pathology slide/region map to the same lesion or tumor site. | Eligible for stronger cross-scale fusion. |

## Required Evidence

A passing gate must record:

- source datasets;
- identifier fields used for matching;
- de-identification or ID translation constraints;
- number of paired patients;
- number of paired lesions, if applicable;
- imaging and pathology timing assumptions;
- clinical endpoint availability;
- missing modality counts;
- exclusions and reasons.

## Gate Output

```yaml
pairing_gate:
  status: pass | fail | needs-human-review
  pairing_level: none | patient-level | lesion-level
  paired_patient_count: integer
  paired_lesion_count: integer | null
  source_datasets: list[string]
  evidence_records: list[string]
  limitations: list[string]
```

## Pass Behavior

When the gate passes, the project may define:

- CT-only baseline;
- WSI-only baseline;
- CT + WSI late fusion;
- CT + WSI intermediate fusion;
- missing-aware CT/WSI fusion.

## Fail Behavior

When the gate fails:

- CT and WSI remain separate branches.
- No CT-pathology fusion model is trained.
- No formal CT-pathology conclusion is claimed.
- The evidence bundle records why the gate failed.

