import ast
import inspect
import tomllib
from pathlib import Path
from typing import Literal

import pytest
from ai_resume_optimizer import (  # type: ignore[import-untyped]
    EvidenceSectionReference,
    MatchAnalysis,
    OptimizationResult,
    RequirementAssessment,
    RequirementEvidence,
    RequirementReference,
    ResumeItem,
    ResumeSection,
)
from ai_resume_optimizer import (
    OptimizedResume as PublicOptimizedResume,
)

import agent_engineering_workbench.resume_mapping as mapping_module
from agent_engineering_workbench.resume_contracts import (
    ResumeAssessmentStatus,
    ResumeMatchRating,
    ResumeSectionType,
)
from agent_engineering_workbench.resume_errors import (
    ResumeOptimizationContractError,
)
from agent_engineering_workbench.resume_mapping import (
    map_resume_optimization_result,
)

type PublicRating = Literal["高", "一般", "低"]
type PublicAssessmentStatus = Literal[
    "well_supported", "underrepresented", "unsupported"
]
type PublicSectionType = Literal[
    "basic_info",
    "summary",
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "other",
]


def make_result(
    *,
    rating: PublicRating = "高",
    assessment_status: PublicAssessmentStatus = "well_supported",
    section_type: PublicSectionType = "experience",
    with_provenance: bool = True,
) -> OptimizationResult:
    item = ResumeItem(
        text="Built reliable Python APIs.",
        source_block_ids=["block-0001"],
        related_requirement_ids=["requirement-1"],
        needs_review=False,
        review_note=None,
    )
    section = ResumeSection(
        section_type=section_type,
        title="Experience",
        items=[item],
        source_block_ids=["block-0001"],
    )
    source_block_ids = (
        [] if assessment_status == "unsupported" else ["block-0001"]
    )
    requirement = RequirementReference(
        requirement_id="requirement-1",
        description="Professional experience designing Python REST APIs.",
        category="experience",
        importance="required",
        source_excerpt="Required: Python REST API experience.",
    )
    evidence = [
        RequirementEvidence(
            source_block_id="block-0001",
            kind="list_item",
            location="experience[0].items[0]",
            excerpt="Built reliable Python APIs.",
            sections=[
                EvidenceSectionReference(
                    section_type="experience",
                    title="Experience",
                )
            ],
        )
    ]
    assessment = RequirementAssessment(
        requirement_id="requirement-1",
        status=assessment_status,
        source_block_ids=source_block_ids,
        reason="The resume provides direct evidence.",
        suggested_action="Keep the quantified example.",
        requirement=(requirement if with_provenance else None),
        evidence=(evidence if with_provenance and source_block_ids else []),
    )
    analysis = MatchAnalysis(
        overall_rating=rating,
        overall_evaluation="Strong evidence for the core requirements.",
        assessments=[assessment],
        main_issues=["Clarify the scale of the API."],
        section_suggestions=["Lead with backend experience."],
        keyword_suggestions=["REST API"],
        truthfulness_risks=["Do not infer team size."],
        content_not_to_add=["Unverified cloud experience."],
    )
    optimized_resume = PublicOptimizedResume(
        sections=[section],
        pending_user_inputs=["Confirm the API request volume."],
        warnings=["One item needs user confirmation."],
    )
    return OptimizationResult(
        analysis=analysis,
        optimized_resume=optimized_resume,
        output_paths={},
        warnings=["PDF layout may affect reading order."],
    )


def test_complete_public_result_maps_without_flattening() -> None:
    mapped = map_resume_optimization_result(make_result())

    assert mapped.model_dump(mode="json") == {
        "analysis": {
            "overall_rating": "high",
            "overall_evaluation": "Strong evidence for the core requirements.",
            "assessments": [
                {
                    "requirement_id": "requirement-1",
                    "status": "well_supported",
                    "source_block_ids": ["block-0001"],
                    "reason": "The resume provides direct evidence.",
                    "suggested_action": "Keep the quantified example.",
                    "requirement": {
                        "requirement_id": "requirement-1",
                        "description": (
                            "Professional experience designing Python REST APIs."
                        ),
                        "category": "experience",
                        "importance": "required",
                        "source_excerpt": "Required: Python REST API experience.",
                    },
                    "evidence": [
                        {
                            "source_block_id": "block-0001",
                            "kind": "list_item",
                            "location": "experience[0].items[0]",
                            "excerpt": "Built reliable Python APIs.",
                            "sections": [
                                {
                                    "section_type": "experience",
                                    "title": "Experience",
                                }
                            ],
                        }
                    ],
                }
            ],
            "main_issues": ["Clarify the scale of the API."],
            "section_suggestions": ["Lead with backend experience."],
            "keyword_suggestions": ["REST API"],
            "truthfulness_risks": ["Do not infer team size."],
            "content_not_to_add": ["Unverified cloud experience."],
        },
        "optimized_resume": {
            "sections": [
                {
                    "section_type": "experience",
                    "title": "Experience",
                    "items": [
                        {
                            "text": "Built reliable Python APIs.",
                            "source_block_ids": ["block-0001"],
                            "related_requirement_ids": ["requirement-1"],
                            "needs_review": False,
                            "review_note": None,
                        }
                    ],
                    "source_block_ids": ["block-0001"],
                }
            ],
            "pending_user_inputs": ["Confirm the API request volume."],
            "warnings": ["One item needs user confirmation."],
        },
        "warnings": ["PDF layout may affect reading order."],
    }


def test_workbench_result_excludes_output_paths() -> None:
    serialized = map_resume_optimization_result(make_result()).model_dump(mode="json")

    assert "output_paths" not in serialized


def test_legacy_public_result_without_provenance_still_maps() -> None:
    assessment = map_resume_optimization_result(
        make_result(with_provenance=False)
    ).analysis.assessments[0]

    assert assessment.requirement_id == "requirement-1"
    assert assessment.source_block_ids == ("block-0001",)
    assert assessment.requirement is None
    assert assessment.evidence == ()


@pytest.mark.parametrize(
    ("external", "expected"),
    (
        ("高", ResumeMatchRating.HIGH),
        ("一般", ResumeMatchRating.MEDIUM),
        ("低", ResumeMatchRating.LOW),
    ),
)
def test_all_public_rating_values_map(
    external: PublicRating,
    expected: ResumeMatchRating,
) -> None:
    assert (
        map_resume_optimization_result(
            make_result(rating=external)
        ).analysis.overall_rating
        is expected
    )


@pytest.mark.parametrize(
    ("external", "expected"),
    (
        ("well_supported", ResumeAssessmentStatus.WELL_SUPPORTED),
        ("underrepresented", ResumeAssessmentStatus.UNDERREPRESENTED),
        ("unsupported", ResumeAssessmentStatus.UNSUPPORTED),
    ),
)
def test_all_public_assessment_status_values_map(
    external: PublicAssessmentStatus,
    expected: ResumeAssessmentStatus,
) -> None:
    assert (
        map_resume_optimization_result(make_result(assessment_status=external))
        .analysis.assessments[0]
        .status
        is expected
    )


@pytest.mark.parametrize(
    "external",
    (
        "basic_info",
        "summary",
        "skills",
        "experience",
        "projects",
        "education",
        "certifications",
        "other",
    ),
)
def test_all_public_section_types_map(external: PublicSectionType) -> None:
    mapped = map_resume_optimization_result(make_result(section_type=external))

    assert mapped.optimized_resume.sections[0].section_type is ResumeSectionType(
        external
    )


@pytest.mark.parametrize(
    ("field", "unknown"),
    (
        ("rating", "unknown-rating"),
        ("assessment", "unknown-assessment"),
        ("section", "unknown-section"),
        ("requirement-category", "unknown-category"),
        ("requirement-importance", "unknown-importance"),
        ("evidence-kind", "unknown-kind"),
        ("evidence-section", "unknown-evidence-section"),
    ),
)
def test_unknown_external_enum_values_fail_closed(
    field: str,
    unknown: str,
) -> None:
    result = make_result()
    if field == "rating":
        result = result.model_copy(
            update={
                "analysis": result.analysis.model_copy(
                    update={"overall_rating": unknown}
                )
            }
        )
    elif field == "assessment":
        assessment = result.analysis.assessments[0].model_copy(
            update={"status": unknown}
        )
        result = result.model_copy(
            update={
                "analysis": result.analysis.model_copy(
                    update={"assessments": [assessment]}
                )
            }
        )
    elif field == "section":
        section = result.optimized_resume.sections[0].model_copy(
            update={"section_type": unknown}
        )
        result = result.model_copy(
            update={
                "optimized_resume": result.optimized_resume.model_copy(
                    update={"sections": [section]}
                )
            }
        )
    else:
        assessment = result.analysis.assessments[0]
        if field == "requirement-category":
            requirement = assessment.requirement.model_copy(
                update={"category": unknown}
            )
            assessment = assessment.model_copy(update={"requirement": requirement})
        elif field == "requirement-importance":
            requirement = assessment.requirement.model_copy(
                update={"importance": unknown}
            )
            assessment = assessment.model_copy(update={"requirement": requirement})
        else:
            evidence = assessment.evidence[0]
            if field == "evidence-kind":
                evidence = evidence.model_copy(update={"kind": unknown})
            else:
                evidence_section = evidence.sections[0].model_copy(
                    update={"section_type": unknown}
                )
                evidence = evidence.model_copy(update={"sections": [evidence_section]})
            assessment = assessment.model_copy(update={"evidence": [evidence]})
        result = result.model_copy(
            update={
                "analysis": result.analysis.model_copy(
                    update={"assessments": [assessment]}
                )
            }
        )

    with pytest.raises(ResumeOptimizationContractError, match="Unknown"):
        map_resume_optimization_result(result)


@pytest.mark.parametrize("mismatch", ("requirement", "evidence"))
def test_misaligned_public_provenance_fails_closed(mismatch: str) -> None:
    result = make_result()
    assessment = result.analysis.assessments[0]
    if mismatch == "requirement":
        requirement = assessment.requirement.model_copy(
            update={"requirement_id": "other-requirement"}
        )
        assessment = assessment.model_copy(update={"requirement": requirement})
    else:
        evidence = assessment.evidence[0].model_copy(
            update={"source_block_id": "other-block"}
        )
        assessment = assessment.model_copy(update={"evidence": [evidence]})
    result = result.model_copy(
        update={
            "analysis": result.analysis.model_copy(
                update={"assessments": [assessment]}
            )
        }
    )

    with pytest.raises(ResumeOptimizationContractError, match="does not match"):
        map_resume_optimization_result(result)


def test_mapping_imports_only_the_optimizer_public_root() -> None:
    tree = ast.parse(inspect.getsource(mapping_module))
    optimizer_imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("ai_resume_optimizer")
    ]

    assert optimizer_imports == ["ai_resume_optimizer"]


def test_backend_metadata_pins_public_optimizer_and_multipart() -> None:
    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    metadata = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependencies = metadata["project"]["dependencies"]
    expected = (
        "ai-resume-optimizer @ "
        "git+https://github.com/Roxin-ChaI/ai-resume-optimizer.git@v0.2.1"
    )

    assert expected in dependencies
    assert "python-multipart" in dependencies
    optimizer_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.startswith("ai-resume-optimizer")
    ]
    assert optimizer_dependencies == [expected]
    assert all("master" not in dependency for dependency in optimizer_dependencies)
    assert all("/Users/" not in dependency for dependency in optimizer_dependencies)
    assert all("-e " not in dependency for dependency in optimizer_dependencies)
