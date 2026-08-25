import inspect
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory as RealTemporaryDirectory
from typing import Never, Protocol

import pytest
from ai_resume_optimizer import (  # type: ignore[import-untyped]
    ConfigurationError as PublicResumeConfigurationError,
)
from fastapi.testclient import TestClient

import agent_engineering_workbench.api.resume as resume_api
from agent_engineering_workbench import dependencies
from agent_engineering_workbench.adapters.resume_optimizer import (
    ResumeOptimizerAdapter,
)
from agent_engineering_workbench.app import app
from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.dependencies import get_resume_optimizer_adapter
from agent_engineering_workbench.resume_contracts import (
    OptimizedResume,
    ResumeAssessmentStatus,
    ResumeEvidenceKind,
    ResumeEvidenceSectionReference,
    ResumeMatchAnalysis,
    ResumeMatchRating,
    ResumeOptimizationItem,
    ResumeOptimizationResult,
    ResumeOptimizationSection,
    ResumeRequirementAssessment,
    ResumeRequirementCategory,
    ResumeRequirementEvidence,
    ResumeRequirementImportance,
    ResumeRequirementReference,
    ResumeSectionType,
)
from agent_engineering_workbench.resume_errors import (
    InvalidResumeInputError,
    ResumeExtractionFailedError,
    ResumeInputTooLargeError,
    ResumeOptimizationConfigurationError,
    ResumeOptimizationInternalError,
    ResumeOptimizationProtocolError,
    ResumeOptimizationUpstreamError,
    ResumeOptimizerClosedError,
    ResumeTruthfulnessError,
    UnsupportedResumeFormatError,
)

JOB_DESCRIPTION = "  Backend role requiring Python and SQL.\n"
UPLOAD_BYTES = b"small controlled document bytes"


class ResponseLike(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> dict[str, object]: ...


def make_result() -> ResumeOptimizationResult:
    return ResumeOptimizationResult(
        analysis=ResumeMatchAnalysis(
            overall_rating=ResumeMatchRating.HIGH,
            overall_evaluation="Strong match.",
            assessments=(
                ResumeRequirementAssessment(
                    requirement_id="requirement-1",
                    status=ResumeAssessmentStatus.WELL_SUPPORTED,
                    source_block_ids=("block-1",),
                    reason="Direct evidence is present.",
                    suggested_action="Keep the example.",
                    requirement=ResumeRequirementReference(
                        requirement_id="requirement-1",
                        description="Professional Python REST API experience.",
                        category=ResumeRequirementCategory.EXPERIENCE,
                        importance=ResumeRequirementImportance.REQUIRED,
                        source_excerpt="Required: Python and REST APIs.",
                    ),
                    evidence=(
                        ResumeRequirementEvidence(
                            source_block_id="block-1",
                            kind=ResumeEvidenceKind.LIST_ITEM,
                            location="experience[0].items[0]",
                            excerpt="Built Python APIs.",
                            sections=(
                                ResumeEvidenceSectionReference(
                                    section_type=ResumeSectionType.EXPERIENCE,
                                    title="Experience",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            main_issues=("Add scale.",),
            section_suggestions=("Lead with experience.",),
            keyword_suggestions=("REST API",),
            truthfulness_risks=("Do not infer team size.",),
            content_not_to_add=("Unverified cloud experience.",),
        ),
        optimized_resume=OptimizedResume(
            sections=(
                ResumeOptimizationSection(
                    section_type=ResumeSectionType.EXPERIENCE,
                    title="Experience",
                    items=(
                        ResumeOptimizationItem(
                            text="Built Python APIs.",
                            source_block_ids=("block-1",),
                            related_requirement_ids=("requirement-1",),
                            needs_review=False,
                            review_note=None,
                        ),
                    ),
                    source_block_ids=("block-1",),
                ),
            ),
            pending_user_inputs=("Confirm request volume.",),
            warnings=("Review the metric.",),
        ),
        warnings=("Layout may affect extraction.",),
    )


class FakeResumeOptimizerAdapter:
    def __init__(
        self,
        outcome: ResumeOptimizationResult | BaseException | None = None,
    ) -> None:
        self.outcome = outcome or make_result()
        self.calls: list[tuple[Path, str]] = []
        self.bytes_during_call: list[bytes] = []
        self.exists_during_call: list[bool] = []
        self.close_calls = 0

    def optimize(
        self,
        *,
        resume_path: Path,
        job_description: str,
    ) -> ResumeOptimizationResult:
        self.calls.append((resume_path, job_description))
        self.exists_during_call.append(resume_path.exists())
        self.bytes_during_call.append(resume_path.read_bytes())
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome

    def close(self) -> None:
        self.close_calls += 1


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def install_fake_adapter(adapter: FakeResumeOptimizerAdapter) -> None:
    app.dependency_overrides[get_resume_optimizer_adapter] = lambda: adapter


def post_resume(
    *,
    filename: str = "resume.docx",
    content: bytes = UPLOAD_BYTES,
    content_type: str | None = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    job_description: str = JOB_DESCRIPTION,
) -> ResponseLike:
    return TestClient(app).post(
        "/api/resume/optimize",
        files={"resume": (filename, content, content_type)},
        data={"job_description": job_description},
    )


def test_docx_upload_returns_workbench_result_and_cleans_temp_file() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume()

    assert response.status_code == 200
    assert len(adapter.calls) == 1
    resume_path, forwarded_description = adapter.calls[0]
    assert resume_path.name == "resume.docx"
    assert resume_path.suffix == ".docx"
    assert adapter.exists_during_call == [True]
    assert adapter.bytes_during_call == [UPLOAD_BYTES]
    assert forwarded_description == JOB_DESCRIPTION
    assert not resume_path.exists()
    payload = response.json()
    assert payload == make_result().model_dump(mode="json")
    validated = ResumeOptimizationResult.model_validate(payload)
    assessment = validated.analysis.assessments[0]
    assert assessment.requirement is not None
    assert assessment.requirement.description == (
        "Professional Python REST API experience."
    )
    assert assessment.evidence[0].excerpt == "Built Python APIs."
    assert assessment.requirement_id == "requirement-1"
    assert assessment.source_block_ids == ("block-1",)
    assert "output_paths" not in payload
    assert "temporary_path" not in payload


def test_pdf_upload_preserves_case_insensitive_suffix() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(
        filename="RESUME.PDF",
        content=b"%PDF controlled bytes",
        content_type="application/pdf",
    )

    assert response.status_code == 200
    assert len(adapter.calls) == 1
    assert adapter.calls[0][0].name == "resume.pdf"
    assert adapter.bytes_during_call == [b"%PDF controlled bytes"]
    assert not adapter.calls[0][0].exists()


def test_legal_suffix_does_not_require_mime_type() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(content_type=None)

    assert response.status_code == 200
    assert len(adapter.calls) == 1


def test_client_filename_cannot_control_temp_path() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(filename="../../secret.docx")

    assert response.status_code == 200
    resume_path = adapter.calls[0][0]
    assert resume_path.name == "resume.docx"
    assert "secret" not in str(resume_path)
    assert resume_path.parent.name.startswith("workbench-resume-")
    assert not resume_path.exists()


def test_missing_file_uses_standard_validation_and_skips_adapter() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/resume/optimize",
        data={"job_description": JOB_DESCRIPTION},
    )

    assert response.status_code == 422
    assert adapter.calls == []


def test_unsupported_suffix_returns_415_without_calling_adapter() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(filename="resume.txt", content_type="text/plain")

    assert response.status_code == 415
    assert adapter.calls == []


def test_empty_upload_returns_422_without_calling_adapter() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(content=b"")

    assert response.status_code == 422
    assert adapter.calls == []


def test_upload_too_large_returns_413_and_cleans_temp_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)
    created_directories: list[Path] = []

    def recording_temporary_directory(
        *,
        prefix: str,
    ) -> RealTemporaryDirectory[str]:
        temporary_directory = RealTemporaryDirectory(prefix=prefix)
        created_directories.append(Path(temporary_directory.name))
        return temporary_directory

    monkeypatch.setattr(resume_api, "MAX_RESUME_UPLOAD_BYTES", 3)
    monkeypatch.setattr(
        resume_api,
        "TemporaryDirectory",
        recording_temporary_directory,
    )

    response = post_resume(content=b"four")

    assert response.status_code == 413
    assert adapter.calls == []
    assert created_directories
    assert all(not directory.exists() for directory in created_directories)


def test_empty_job_description_returns_422_without_calling_adapter() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(job_description="   ")

    assert response.status_code == 422
    assert adapter.calls == []


def test_job_description_too_large_returns_413_without_calling_adapter() -> None:
    adapter = FakeResumeOptimizerAdapter()
    install_fake_adapter(adapter)

    response = post_resume(
        job_description="x" * (resume_api.MAX_JOB_DESCRIPTION_CHARACTERS + 1)
    )

    assert response.status_code == 413
    assert adapter.calls == []


@pytest.mark.parametrize(
    ("adapter_error", "expected_status"),
    (
        (UnsupportedResumeFormatError("secret"), 415),
        (ResumeInputTooLargeError("secret"), 413),
        (InvalidResumeInputError("secret"), 422),
        (ResumeExtractionFailedError("secret"), 422),
        (ResumeOptimizationUpstreamError("secret"), 502),
        (ResumeOptimizationProtocolError("secret"), 502),
        (ResumeTruthfulnessError("secret"), 502),
        (ResumeOptimizationConfigurationError("secret"), 500),
        (ResumeOptimizerClosedError("secret"), 500),
        (ResumeOptimizationInternalError("secret"), 500),
    ),
)
def test_domain_errors_map_to_safe_http_status(
    adapter_error: Exception,
    expected_status: int,
) -> None:
    adapter = FakeResumeOptimizerAdapter(adapter_error)
    install_fake_adapter(adapter)

    response = post_resume()

    assert response.status_code == expected_status
    assert "secret" not in response.text
    assert len(adapter.calls) == 1
    assert not adapter.calls[0][0].exists()


def test_unknown_adapter_error_returns_safe_500_and_cleans_temp_file() -> None:
    adapter = FakeResumeOptimizerAdapter(RuntimeError("secret internal detail"))
    install_fake_adapter(adapter)

    response = post_resume()

    assert response.status_code == 500
    assert "secret" not in response.text
    assert len(adapter.calls) == 1
    assert not adapter.calls[0][0].exists()


def test_request_scoped_dependency_closes_after_success() -> None:
    adapter = FakeResumeOptimizerAdapter()
    creation_count = 0

    def override_dependency() -> Iterator[FakeResumeOptimizerAdapter]:
        nonlocal creation_count
        creation_count += 1
        try:
            yield adapter
        finally:
            adapter.close()

    app.dependency_overrides[get_resume_optimizer_adapter] = override_dependency

    response = post_resume()

    assert response.status_code == 200
    assert creation_count == 1
    assert adapter.close_calls == 1


def test_request_scoped_dependency_closes_after_adapter_error() -> None:
    adapter = FakeResumeOptimizerAdapter(
        ResumeOptimizationUpstreamError("secret upstream detail")
    )

    def override_dependency() -> Iterator[FakeResumeOptimizerAdapter]:
        try:
            yield adapter
        finally:
            adapter.close()

    app.dependency_overrides[get_resume_optimizer_adapter] = override_dependency

    response = post_resume()

    assert response.status_code == 502
    assert adapter.close_calls == 1
    assert len(adapter.calls) == 1


@dataclass(frozen=True, repr=False)
class FakeResumeOptimizerConfig:
    deepseek_api_key: str
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 60.0

    def __repr__(self) -> str:
        return (
            "FakeResumeOptimizerConfig(deepseek_api_key=<redacted>, "
            f"deepseek_model={self.deepseek_model!r}, "
            f"deepseek_timeout_seconds={self.deepseek_timeout_seconds!r})"
        )


class FakeProductionRunner:
    def __init__(self) -> None:
        self.close_calls = 0

    def optimize(self, *, resume_path: Path, job_description: str) -> Never:
        raise AssertionError(
            f"Production runner must not execute in tests: {resume_path}, "
            f"{job_description}"
        )

    def close(self) -> None:
        self.close_calls += 1


def test_production_dependency_uses_public_factory_and_closes_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeProductionRunner()
    captured_configs: list[FakeResumeOptimizerConfig] = []

    def fake_factory(config: FakeResumeOptimizerConfig) -> FakeProductionRunner:
        captured_configs.append(config)
        return runner

    monkeypatch.setattr(
        dependencies, "ResumeOptimizerConfig", FakeResumeOptimizerConfig
    )
    monkeypatch.setattr(dependencies, "create_resume_optimizer", fake_factory)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            deepseek_api_key="not-a-real-key",
            model_name="deepseek-v4-flash",
        ),
    )

    with contextmanager(dependencies.get_resume_optimizer_adapter)() as adapter:
        assert isinstance(adapter, ResumeOptimizerAdapter)
        assert runner.close_calls == 0

    assert runner.close_calls == 1
    assert captured_configs == [
        FakeResumeOptimizerConfig(
            deepseek_api_key="not-a-real-key",
            deepseek_model="deepseek-v4-flash",
        )
    ]
    assert "not-a-real-key" not in repr(captured_configs[0])


def test_production_dependency_closes_when_request_scope_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeProductionRunner()
    monkeypatch.setattr(
        dependencies, "ResumeOptimizerConfig", FakeResumeOptimizerConfig
    )
    monkeypatch.setattr(
        dependencies,
        "create_resume_optimizer",
        lambda config: runner,
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key="not-a-real-key"),
    )
    expected = RuntimeError("request failed")

    with (
        pytest.raises(RuntimeError) as captured,
        contextmanager(dependencies.get_resume_optimizer_adapter)(),
    ):
        raise expected

    assert captured.value is expected
    assert runner.close_calls == 1


@pytest.mark.parametrize(
    "settings",
    (
        Settings(deepseek_api_key=None),
        Settings(deepseek_api_key="   "),
        Settings(model_provider="unsupported", deepseek_api_key="not-a-real-key"),
    ),
)
def test_production_dependency_rejects_invalid_workbench_configuration(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)

    with (
        pytest.raises(ResumeOptimizationConfigurationError),
        contextmanager(dependencies.get_resume_optimizer_adapter)(),
    ):
        pass


def test_public_factory_configuration_error_maps_without_creating_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause = PublicResumeConfigurationError("secret configuration detail")

    def fail_config(**_kwargs: object) -> Never:
        raise cause

    monkeypatch.setattr(dependencies, "ResumeOptimizerConfig", fail_config)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key="not-a-real-key"),
    )

    with (
        pytest.raises(ResumeOptimizationConfigurationError) as captured,
        contextmanager(dependencies.get_resume_optimizer_adapter)(),
    ):
        pass

    assert captured.value.__cause__ is cause
    assert "secret" not in str(captured.value)


def test_production_configuration_failure_returns_safe_http_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key=None),
    )

    response = post_resume()

    assert response.status_code == 500
    assert response.json() == {"detail": "Resume optimizer is not configured."}


def test_resume_route_is_registered_without_regressing_existing_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/resume/optimize" in paths
    assert "/api/github/review" in paths
    assert "/api/context/compress" in paths
    assert "/api/research/web" in paths
    assert "/api/research/knowledge" in paths
    assert "/health" in paths


def test_production_imports_use_only_public_optimizer_boundary() -> None:
    dependency_source = Path(dependencies.__file__).read_text(encoding="utf-8")
    api_source = Path(resume_api.__file__).read_text(encoding="utf-8")
    resume_dependency_source = inspect.getsource(
        dependencies.get_resume_optimizer_adapter
    )

    assert "from ai_resume_optimizer import" in dependency_source
    assert "from ai_resume_optimizer." not in dependency_source
    assert "ai_resume_optimizer" not in api_source
    combined_source = resume_dependency_source + api_source
    assert all(
        forbidden not in combined_source.lower()
        for forbidden in (
            "subprocess",
            "deepseekmodelclient",
            "openai import",
            ".cli",
            "exporter",
        )
    )
