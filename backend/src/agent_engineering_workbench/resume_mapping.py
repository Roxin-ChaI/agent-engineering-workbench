from collections.abc import Mapping

from ai_resume_optimizer import OptimizationResult  # type: ignore[import-untyped]

from agent_engineering_workbench.resume_contracts import (
    OptimizedResume,
    ResumeAssessmentStatus,
    ResumeMatchAnalysis,
    ResumeMatchRating,
    ResumeOptimizationItem,
    ResumeOptimizationResult,
    ResumeOptimizationSection,
    ResumeRequirementAssessment,
    ResumeSectionType,
)
from agent_engineering_workbench.resume_errors import (
    ResumeOptimizationContractError,
)

_RATING_MAP: Mapping[str, ResumeMatchRating] = {
    "高": ResumeMatchRating.HIGH,
    "一般": ResumeMatchRating.MEDIUM,
    "低": ResumeMatchRating.LOW,
}
_ASSESSMENT_STATUS_MAP: Mapping[str, ResumeAssessmentStatus] = {
    "well_supported": ResumeAssessmentStatus.WELL_SUPPORTED,
    "underrepresented": ResumeAssessmentStatus.UNDERREPRESENTED,
    "unsupported": ResumeAssessmentStatus.UNSUPPORTED,
}
_SECTION_TYPE_MAP: Mapping[str, ResumeSectionType] = {
    "basic_info": ResumeSectionType.BASIC_INFO,
    "summary": ResumeSectionType.SUMMARY,
    "skills": ResumeSectionType.SKILLS,
    "experience": ResumeSectionType.EXPERIENCE,
    "projects": ResumeSectionType.PROJECTS,
    "education": ResumeSectionType.EDUCATION,
    "certifications": ResumeSectionType.CERTIFICATIONS,
    "other": ResumeSectionType.OTHER,
}


def _map_enum_value[EnumT](
    value: str,
    mapping: Mapping[str, EnumT],
    field_name: str,
) -> EnumT:
    try:
        return mapping[value]
    except KeyError as exc:
        raise ResumeOptimizationContractError(
            f"Unknown Resume Optimizer {field_name}: {value!r}"
        ) from exc


def map_resume_optimization_result(
    result: OptimizationResult,
) -> ResumeOptimizationResult:
    """Map the public optimizer result to immutable Workbench contracts."""

    analysis = result.analysis
    optimized_resume = result.optimized_resume
    return ResumeOptimizationResult(
        analysis=ResumeMatchAnalysis(
            overall_rating=_map_enum_value(
                analysis.overall_rating,
                _RATING_MAP,
                "overall_rating",
            ),
            overall_evaluation=analysis.overall_evaluation,
            assessments=tuple(
                ResumeRequirementAssessment(
                    requirement_id=assessment.requirement_id,
                    status=_map_enum_value(
                        assessment.status,
                        _ASSESSMENT_STATUS_MAP,
                        "assessment status",
                    ),
                    source_block_ids=tuple(assessment.source_block_ids),
                    reason=assessment.reason,
                    suggested_action=assessment.suggested_action,
                )
                for assessment in analysis.assessments
            ),
            main_issues=tuple(analysis.main_issues),
            section_suggestions=tuple(analysis.section_suggestions),
            keyword_suggestions=tuple(analysis.keyword_suggestions),
            truthfulness_risks=tuple(analysis.truthfulness_risks),
            content_not_to_add=tuple(analysis.content_not_to_add),
        ),
        optimized_resume=OptimizedResume(
            sections=tuple(
                ResumeOptimizationSection(
                    section_type=_map_enum_value(
                        section.section_type,
                        _SECTION_TYPE_MAP,
                        "section_type",
                    ),
                    title=section.title,
                    items=tuple(
                        ResumeOptimizationItem(
                            text=item.text,
                            source_block_ids=tuple(item.source_block_ids),
                            related_requirement_ids=tuple(item.related_requirement_ids),
                            needs_review=item.needs_review,
                            review_note=item.review_note,
                        )
                        for item in section.items
                    ),
                    source_block_ids=tuple(section.source_block_ids),
                )
                for section in optimized_resume.sections
            ),
            pending_user_inputs=tuple(optimized_resume.pending_user_inputs),
            warnings=tuple(optimized_resume.warnings),
        ),
        warnings=tuple(result.warnings),
    )
