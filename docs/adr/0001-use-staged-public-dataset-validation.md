# Use staged public-dataset validation

Status: accepted

BrainFusion-Agents will not assume that a single public cohort provides patient-level paired brain PET, brain MR, CT, and pathology WSI. The project will use staged validation: ADNI/OASIS-3 for PET/MR, TCGA/GDC and pathology benchmarks for WSI preprocessing, TCIA/IDC lung CT collections for CT, and only verified paired cancer cohorts for CT-pathology fusion.

## Consequences

- The main claim must come from the PET/MR mainline.
- WSI and CT branches can mature independently.
- CT-pathology fusion remains an extension until pairing is proven.

