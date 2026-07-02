# BrainFusion-Agents Context

BrainFusion-Agents is a research project for multi-agent multimodal medical AI workflows. The domain language focuses on staged public-dataset validation, PET/MR fusion, WSI preprocessing, CT agent prototyping, and evidence-producing agent traces.

## Language

**Public dataset strategy**:
A staged validation strategy that uses different public datasets for different modality branches instead of requiring one fully paired four-modality cohort.
_Avoid_: Universal dataset, all-in-one cohort.

**PET/MR mainline**:
The primary publishable workflow using paired or alignable brain PET and MR data for Alzheimer's disease classification and fusion experiments.
_Avoid_: Brain branch, neuro branch.

**External validation set**:
A dataset not used as the primary training source and reserved to test whether PET/MR results generalize beyond the main development cohort.
_Avoid_: Test addon, backup dataset.

**WSI preprocessing branch**:
The pathology workflow that prepares whole-slide images through quality control, tissue detection, artifact filtering, stain normalization, patch extraction, and embedding extraction.
_Avoid_: Pathology fusion by default.

**CT branch**:
The CT workflow that prototypes lesion or cancer imaging processing, quality control, segmentation, classification, or radiomics baselines.
_Avoid_: Radiology branch when the modality is specifically CT.

**CT-pathology fusion**:
A cross-scale fusion workflow that combines CT-derived patient or lesion evidence with WSI-derived pathology evidence after patient-level pairing is confirmed.
_Avoid_: Pixel-level CT/pathology registration.

**Patient-level pairing**:
A verified mapping that shows two modalities belong to the same patient or case according to dataset identifiers and access rules.
_Avoid_: Assumed pairing, dataset-level pairing.

**Lesion-level pairing**:
A verified mapping that shows CT findings and pathology evidence correspond to the same lesion or tumor site.
_Avoid_: Spatial registration unless true geometric alignment exists.

**Pixel-level fusion**:
Fusion that combines modalities in a common spatial image coordinate system, appropriate for PET/MR after preprocessing and registration.
_Avoid_: Using this term for CT-pathology.

**Cross-scale fusion**:
Fusion across different biological or imaging scales, especially CT with WSI, where evidence is linked by patient, lesion, region, or clinical labels rather than common pixels.
_Avoid_: Pixel-level fusion for WSI and CT.

**Multi-agent workflow**:
A coordinated pipeline where specialized agents perform data availability checks, preprocessing, quality control, model execution, fusion, evidence collection, and failure handling.
_Avoid_: One monolithic fusion script.

**Agent trace**:
A structured record of an agent run containing input modality, model, parameters, QC result, failure state, human review state, and evidence.
_Avoid_: Log file when the record is meant to support conclusions.

**Evidence trail**:
The set of traces and artifacts that justify a workflow decision, model output, QC gate, or final experimental conclusion.
_Avoid_: Explanation only, notes.

**QC gate**:
A required quality-control decision point that can pass, fail, warn, or request human review before downstream workflow steps proceed.
_Avoid_: Optional sanity check.

**Failure recovery**:
The workflow behavior that records a failure, selects a fallback path where allowed, and preserves enough evidence for review.
_Avoid_: Silent retry.

**Main conclusion**:
A claim supported by the MVP PET/MR experiments and their external validation.
_Avoid_: Claiming extension results as core evidence.

**Extension experiment**:
An experiment that expands WSI, CT, or CT-pathology capability but does not carry the main project conclusion unless its data pairing and validation gates are satisfied.
_Avoid_: Secondary main result.

**Missing-aware fusion**:
Fusion that explicitly models absent modalities and does not treat missing data as a successful negative finding.
_Avoid_: Dropping missing cases without reporting.

## Example Dialogue

Researcher: "Can we present CT and pathology as the same kind of fusion as PET/MR?"

Agent: "No. PET/MR can support pixel-level fusion after registration. CT-pathology is cross-scale fusion and only becomes a formal experiment after patient-level pairing is verified."

Researcher: "Then what is the MVP?"

Agent: "The MVP is the PET/MR mainline using ADNI for primary development and OASIS-3 as the external validation set. WSI preprocessing and CT branch work are extension experiments until their gates are met."

