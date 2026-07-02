import unittest

from brainfusion_agents import (
    AgentTrace,
    ConclusionSupport,
    EvidenceBundle,
    FailureState,
    HumanReviewState,
    QCResult,
    validate_trace,
)


def make_trace(**overrides):
    values = {
        "trace_id": "trace-1",
        "workflow_id": "pet_mr_mainline",
        "agent_name": "PET/MR Fusion Agent",
        "agent_version": "0.1.0",
        "dataset_id": "adni",
        "subject_id": "subject-1",
        "session_id": "session-1",
        "input_modalities": ("PET", "MR"),
        "task": "pet_mr_fusion_baseline",
        "model_name": "baseline",
        "model_version": "0.1.0",
        "parameters": {},
        "qc": QCResult(status="pass", checks=("pet_present", "mr_present")),
        "failure": FailureState(failed=False, category="none"),
        "human_review": HumanReviewState(required=False, completed=False),
        "evidence": EvidenceBundle(source_records=("adni:subject-1:session-1",)),
        "conclusion_support": ConclusionSupport(supports_main_conclusion=True),
    }
    values.update(overrides)
    return AgentTrace(**values)


class TraceValidationTests(unittest.TestCase):
    def test_pet_mr_trace_can_support_main_conclusion(self) -> None:
        trace = make_trace()

        self.assertEqual(validate_trace(trace), ())

    def test_ct_trace_cannot_support_main_conclusion(self) -> None:
        trace = make_trace(
            workflow_id="ct_branch",
            input_modalities=("CT",),
            dataset_id="lidc-idri",
        )

        errors = validate_trace(trace)

        self.assertIn("Only PET/MR mainline traces can support the main conclusion.", errors)

    def test_ct_pathology_extension_requires_passed_pairing_gate(self) -> None:
        trace = make_trace(
            workflow_id="ct_pathology_fusion",
            input_modalities=("CT", "WSI"),
            dataset_id="tcia-tcga-paired-candidates",
            parameters={"pairing_gate_status": "fail", "pairing_level": "none"},
            conclusion_support=ConclusionSupport(supports_extension_experiment=True),
        )

        errors = validate_trace(trace)

        self.assertIn("CT-pathology extension traces require a passed pairing gate.", errors)

    def test_incomplete_human_review_blocks_conclusion_support(self) -> None:
        trace = make_trace(
            human_review=HumanReviewState(required=True, completed=False),
        )

        errors = validate_trace(trace)

        self.assertIn(
            "Trace cannot support a conclusion while required human review is incomplete.",
            errors,
        )


if __name__ == "__main__":
    unittest.main()

