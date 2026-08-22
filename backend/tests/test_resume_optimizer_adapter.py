import ast
import inspect
from collections.abc import Callable
from pathlib import Path

import pytest
from ai_resume_optimizer import (  # type: ignore[import-untyped]
    ConfigurationError as PublicConfigurationError,
)
from ai_resume_optimizer import (
    InputError as PublicInputError,
)
from ai_resume_optimizer import (
    InputTooLargeError as PublicInputTooLargeError,
)
from ai_resume_optimizer import (
    MatchAnalysis,
    OptimizationResult,
    RequirementAssessment,
    ResumeItem,
    ResumeSection,
)
from ai_resume_optimizer import (
    ModelCallError as PublicModelCallError,
)
from ai_resume_optimizer import (
    ModelOutputError as PublicModelOutputError,
)
from ai_resume_optimizer import (
    OptimizedResume as PublicOptimizedResume,
)
from ai_resume_optimizer import (
    OutputError as PublicOutputError,
)
from ai_resume_optimizer import (
    ResumeExtractionError as PublicResumeExtractionError,
)
from ai_resume_optimizer import (
    ResumeOptimizerClosedError as PublicResumeOptimizerClosedError,
)
from ai_resume_optimizer import (
    TruthfulnessError as PublicTruthfulnessError,
)
from ai_resume_optimizer import (
    UnsupportedFormatError as PublicUnsupportedFormatError,
)

import agent_engineering_workbench.adapters.resume_optimizer as adapter_module
from agent_engineering_workbench.adapters.resume_optimizer import (
    ResumeOptimizerAdapter,
)
from agent_engineering_workbench.resume_errors import (
    InvalidResumeInputError,
    ResumeExtractionFailedError,
    ResumeInputTooLargeError,
    ResumeOptimizationConfigurationError,
    ResumeOptimizationContractError,
    ResumeOptimizationInternalError,
    ResumeOptimizationProtocolError,
    ResumeOptimizationUpstreamError,
    ResumeOptimizerClosedError,
    ResumeTruthfulnessError,
    UnsupportedResumeFormatError,
)
from agent_engineering_workbench.resume_mapping import (
    map_resume_optimization_result,
)


def make_result() -> OptimizationResult:
    assessment = RequirementAssessment(
        requirement_id="requirement-1",
        status="well_supported",
        source_block_ids=["block-1"],
        reason="Direct evidence is present.",
        suggested_action="Keep the example.",
    )
    analysis = MatchAnalysis(
        overall_rating="高",
        overall_evaluation="Strong match.",
        assessments=[assessment],
        main_issues=["Add scale."],
        section_suggestions=["Lead with experience."],
        keyword_suggestions=["REST API"],
        truthfulness_risks=["Do not infer team size."],
        content_not_to_add=["Unverified cloud experience."],
    )
    item = ResumeItem(
        text="Built Python APIs.",
        source_block_ids=["block-1"],
        related_requirement_ids=["requirement-1"],
        needs_review=False,
        review_note=None,
    )
    optimized_resume = PublicOptimizedResume(
        sections=[
            ResumeSection(
                section_type="experience",
                title="Experience",
                items=[item],
                source_block_ids=["block-1"],
            )
        ],
        pending_user_inputs=["Confirm request volume."],
        warnings=["Review the metric."],
    )
    return OptimizationResult(
        analysis=analysis,
        optimized_resume=optimized_resume,
        output_paths={},
        warnings=["Layout may affect extraction."],
    )


class FakeRunner:
    def __init__(
        self,
        result: OptimizationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or make_result()
        self.error = error
        self.optimize_calls: list[tuple[Path, str]] = []
        self.close_calls = 0

    def optimize(
        self,
        *,
        resume_path: Path,
        job_description: str,
    ) -> OptimizationResult:
        self.optimize_calls.append((resume_path, job_description))
        if self.error is not None:
            raise self.error
        return self.result

    def close(self) -> None:
        self.close_calls += 1


def test_success_maps_result_and_forwards_inputs_exactly_once() -> None:
    runner = FakeRunner()
    adapter = ResumeOptimizerAdapter(runner)
    resume_path = Path("candidate resume.docx")
    job_description = "  Raw job description.\n"

    result = adapter.optimize(
        resume_path=resume_path,
        job_description=job_description,
    )

    assert len(runner.optimize_calls) == 1
    forwarded_path, forwarded_description = runner.optimize_calls[0]
    assert forwarded_path is resume_path
    assert forwarded_description is job_description
    assert result == map_resume_optimization_result(runner.result)
    assert result.analysis.overall_evaluation == "Strong match."
    assert result.analysis.main_issues == ("Add scale.",)
    assert result.optimized_resume.sections[0].items[0].text == "Built Python APIs."
    assert result.warnings == ("Layout may affect extraction.",)
    assert "output_paths" not in result.model_dump(mode="json")


def test_successful_optimize_can_be_followed_by_close() -> None:
    runner = FakeRunner()
    adapter = ResumeOptimizerAdapter(runner)

    adapter.optimize(
        resume_path=Path("resume.pdf"),
        job_description="Python role",
    )
    adapter.close()

    assert len(runner.optimize_calls) == 1
    assert runner.close_calls == 1


def test_close_is_idempotent_and_closes_runner_once() -> None:
    runner = FakeRunner()
    adapter = ResumeOptimizerAdapter(runner)

    adapter.close()
    adapter.close()

    assert runner.close_calls == 1


def test_optimize_after_close_fails_before_calling_runner() -> None:
    runner = FakeRunner()
    adapter = ResumeOptimizerAdapter(runner)
    adapter.close()

    with pytest.raises(ResumeOptimizerClosedError, match="unavailable"):
        adapter.optimize(
            resume_path=Path("resume.pdf"),
            job_description="Python role",
        )

    assert runner.optimize_calls == []
    assert runner.close_calls == 1


type PublicErrorFactory = Callable[[str], Exception]
type WorkbenchErrorType = type[Exception]


@pytest.mark.parametrize(
    ("public_error", "workbench_error"),
    (
        (PublicConfigurationError, ResumeOptimizationConfigurationError),
        (PublicInputError, InvalidResumeInputError),
        (PublicUnsupportedFormatError, UnsupportedResumeFormatError),
        (PublicInputTooLargeError, ResumeInputTooLargeError),
        (PublicResumeExtractionError, ResumeExtractionFailedError),
        (PublicModelCallError, ResumeOptimizationUpstreamError),
        (PublicModelOutputError, ResumeOptimizationProtocolError),
        (PublicTruthfulnessError, ResumeTruthfulnessError),
        (PublicOutputError, ResumeOptimizationInternalError),
        (PublicResumeOptimizerClosedError, ResumeOptimizerClosedError),
    ),
)
def test_public_errors_map_explicitly_with_chaining(
    public_error: PublicErrorFactory,
    workbench_error: WorkbenchErrorType,
) -> None:
    cause = public_error("sensitive upstream detail")
    runner = FakeRunner(error=cause)
    adapter = ResumeOptimizerAdapter(runner)

    with pytest.raises(workbench_error) as captured:
        adapter.optimize(
            resume_path=Path("resume.pdf"),
            job_description="Python role",
        )

    assert len(runner.optimize_calls) == 1
    assert captured.value.__cause__ is cause
    assert "sensitive upstream detail" not in str(captured.value)


def test_failure_does_not_prevent_caller_from_closing_runner_once() -> None:
    runner = FakeRunner(error=PublicModelCallError("upstream detail"))
    adapter = ResumeOptimizerAdapter(runner)

    with pytest.raises(ResumeOptimizationUpstreamError):
        adapter.optimize(
            resume_path=Path("resume.pdf"),
            job_description="Python role",
        )
    adapter.close()
    adapter.close()

    assert len(runner.optimize_calls) == 1
    assert runner.close_calls == 1


def test_unknown_exception_maps_to_safe_internal_error() -> None:
    cause = RuntimeError("database password and internal detail")
    runner = FakeRunner(error=cause)
    adapter = ResumeOptimizerAdapter(runner)

    with pytest.raises(ResumeOptimizationInternalError) as captured:
        adapter.optimize(
            resume_path=Path("resume.pdf"),
            job_description="Python role",
        )

    assert len(runner.optimize_calls) == 1
    assert captured.value.__cause__ is cause
    assert str(captured.value) == "Resume optimizer failed during internal processing."
    assert "password" not in str(captured.value)


def test_mapping_contract_drift_maps_to_safe_protocol_error() -> None:
    result = make_result()
    invalid_analysis = result.analysis.model_copy(
        update={"overall_rating": "unexpected-rating"}
    )
    runner = FakeRunner(result=result.model_copy(update={"analysis": invalid_analysis}))
    adapter = ResumeOptimizerAdapter(runner)

    with pytest.raises(ResumeOptimizationProtocolError) as captured:
        adapter.optimize(
            resume_path=Path("resume.pdf"),
            job_description="Python role",
        )

    assert len(runner.optimize_calls) == 1
    assert isinstance(captured.value.__cause__, ResumeOptimizationContractError)
    assert str(captured.value) == "Resume optimizer returned an incompatible result."
    assert "unexpected-rating" not in str(captured.value)


def test_adapter_imports_only_the_resume_optimizer_public_root() -> None:
    source = inspect.getsource(adapter_module)
    tree = ast.parse(source)
    optimizer_imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("ai_resume_optimizer")
    ]

    assert optimizer_imports
    assert set(optimizer_imports) == {"ai_resume_optimizer"}
    assert "subprocess" not in source
    assert "cli" not in source.lower()
    assert "deepseek" not in source.lower()
