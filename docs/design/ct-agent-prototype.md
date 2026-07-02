# CT Agent Prototype

The CT branch prototypes CT processing and baseline evidence using public lung CT collections. It is independent of WSI until a CT-pathology pairing gate passes.

## Research Role

The CT Agent should establish CT ingestion, QC, and baseline output conventions that can later support radiopathomics. The first useful target is LIDC-IDRI because it is mature and suitable for lung nodule workflows.

## Dataset Roles

| Dataset group | Role |
| --- | --- |
| LIDC-IDRI | Initial CT prototype for lung nodule segmentation, classification, and QC. |
| NSCLC-Radiomics | Cancer CT expansion for radiomics and prognosis-oriented baselines. |
| NLST via TCIA/IDC | Larger lung screening CT expansion and annotation review candidate. |

## Agent Tasks

1. CT collection inventory and metadata capture.
2. DICOM or derived image availability check.
3. CT quality-control checks.
4. Lesion/nodule annotation availability check.
5. Segmentation, classification, or radiomics baseline selection.
6. Feature and metric manifest generation.
7. Trace generation.

## Output Manifest

Each CT run should produce:

- dataset ID;
- patient/case ID;
- study and series references;
- CT protocol metadata where available;
- lesion/nodule reference if applicable;
- baseline type: segmentation, classification, radiomics, or feature extraction;
- output artifact references;
- QC status;
- trace ID.

## QC Gates

- CT series readable.
- Study/series metadata sufficient for the chosen task.
- Required annotations available when using annotation-dependent baselines.
- Baseline output generated.
- Trace and manifest complete.

## Boundaries

- CT-only results are extension evidence unless connected to the PET/MR mainline by a later project decision.
- CT-pathology fusion cannot begin from CT co-availability alone.
- CT and WSI must remain separate branches if the pairing gate fails.

