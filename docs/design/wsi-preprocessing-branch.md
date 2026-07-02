# WSI Preprocessing Branch

The WSI preprocessing branch prepares pathology whole-slide images for downstream benchmarking and future fusion. It does not assume spatial or patient-level pairing with PET/MR or CT.

## Research Role

This branch demonstrates that BrainFusion-Agents can manage pathology preprocessing and produce auditable WSI embeddings. It is an extension branch until paired CT/WSI evidence is verified.

## Dataset Roles

| Dataset group | Role |
| --- | --- |
| TCGA/GDC WSI | Large-scale WSI preprocessing and embedding extraction. |
| CAMELYON16/17 | Metastasis-oriented WSI QC and patch/task benchmark. |
| PANDA | Prostate WSI grading benchmark and patch classification reference. |
| IGNITE | NSCLC pathology ROI/cell/tissue annotation candidate for preprocessing evaluation. |

## Agent Tasks

1. Slide inventory and metadata capture.
2. Tissue detection.
3. Artifact filtering.
4. Stain normalization decision and parameter recording.
5. Patch extraction.
6. Embedding extraction with a pathology foundation model candidate.
7. QC report generation.
8. Patch and embedding manifest generation.

## Output Manifest

Each processed WSI should produce a manifest record with:

- dataset ID;
- case or slide ID;
- slide file reference;
- magnification or resolution metadata where available;
- tissue mask artifact;
- excluded regions and reasons;
- patch count;
- embedding model and version;
- QC status;
- trace ID.

## QC Gates

- Slide readable.
- Tissue area above minimum threshold.
- Artifact filtering completed or explicitly skipped.
- Patch extraction completed.
- Embedding extraction completed.
- Output manifest written.

## Boundaries

- This branch does not perform PET/MR fusion.
- This branch does not perform CT-pathology fusion without the pairing gate.
- WSI embeddings are evidence artifacts, not clinical conclusions by themselves.

