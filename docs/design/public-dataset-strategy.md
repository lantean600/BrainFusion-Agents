# Public Dataset Strategy

This project uses a staged, multi-dataset strategy because a single public dataset is unlikely to cover brain PET, brain MR, CT, and pathology WSI with complete patient-level pairing.

Source pointers were checked on 2026-07-02 for planning purposes. Dataset access rules can change and must be rechecked before download or publication.

## Dataset Matrix

| Data type | Dataset | Project role | Access and limits | Pairing status |
| --- | --- | --- | --- | --- |
| Brain PET/MR | ADNI | Primary PET/MR mainline; AD/MCI/CN classification; PET/MR preprocessing and QC | Requires application through LONI IDA. ADNI provides clinical, imaging, genetic, and biomarker data to approved researchers. | Use as primary PET/MR cohort after subject/session alignment. |
| Brain PET/MR | OASIS-3 | External validation for PET/MR workflow | Requires OASIS/NITRC access request. OASIS-3 reports 1,378 participants, 2,842 MR sessions, more than 2,157 PET scans, and 451 Tau PET sessions. | Use as independent validation, not training source. |
| Brain imaging supplement | OpenNeuro | BIDS workflow testing and MRI tooling checks | Open data portal; PET/MR pairing is not stable enough for the mainline. | Not a PET/MR main dataset. |
| CT | LIDC-IDRI | Lung nodule CT segmentation, classification, QC baseline | Public TCIA collection; useful for CT agent prototype and annotation-driven baselines. | CT-only branch unless linked to separate pathology evidence. |
| CT | NSCLC-Radiomics / NLST via TCIA or IDC | Lung cancer CT, radiomics, prognosis, AI-derived annotation review | TCIA and IDC support cancer imaging browsing and programmatic/cloud workflows; exact collection terms must be checked before use. | CT branch and candidate pairing review. |
| Pathology WSI | TCGA via GDC | Large-scale WSI preprocessing and foundation-model feature extraction | GDC hosts TCGA data; TCGA/CPTAC WSI usage is referenced by UNI and related pathology work. | WSI branch; pair with TCIA only after ID audit. |
| Pathology WSI | CAMELYON16/17, PANDA, IGNITE | WSI QC, tissue detection, patch classification, preprocessing benchmarks | Benchmark datasets with task-specific labels; licenses and download steps vary. | Benchmark branch, not assumed paired with CT or PET/MR. |
| CT + pathology | TCIA + TCGA/GDC paired cancer cohorts | Radiopathomics and CT/WSI fusion extension | Must audit patient IDs, cancer type, imaging dates, pathology slide availability, and clinical endpoints. | Formal fusion only after pairing gate passes. |
| CT + pathology | NSCLC radiopathomics public cohorts | Missing-aware CT/WSI survival or prognosis extension | Use literature and collection metadata to confirm modality availability and identifiers. | Extension candidate. |

## Access Policy

- No controlled dataset is downloaded until a human confirms approval status, storage location, and data-use terms.
- Dataset records must include access status: `not-requested`, `requested`, `approved`, `downloaded`, `indexed`, or `excluded`.
- Any publication claim must cite the exact dataset version, access date, preprocessing version, and exclusion criteria.

## Decision Rules

- PET/MR mainline: ADNI first, OASIS-3 external validation second.
- WSI branch: TCGA/GDC for scale; CAMELYON/PANDA/IGNITE for labeled QC and preprocessing evaluation.
- CT branch: LIDC-IDRI first for prototype; NSCLC-Radiomics/NLST for cancer CT expansion.
- CT-pathology fusion: do not start modeling until pairing audit passes.

## Source Pointers

- ADNI data access and modality overview: https://adni.loni.usc.edu/data-samples/adni-data/
- ADNI PET overview: https://adni.loni.usc.edu/data-samples/adni-data/neuroimaging/pet/
- ADNI MRI overview: https://adni.loni.usc.edu/data-samples/adni-data/neuroimaging/mri/
- OASIS datasets: https://www.oasis-brains.org/
- OpenNeuro: https://openneuro.org/
- TCIA: https://www.cancerimagingarchive.net/
- IDC portal: https://portal.imaging.datacommons.cancer.gov/
- GDC portal: https://portal.gdc.cancer.gov/
- UNI Nature Medicine paper: https://www.nature.com/articles/s41591-024-02857-3

