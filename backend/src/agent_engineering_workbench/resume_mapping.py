from collections.abc import Mapping

from ai_resume_optimizer import (  # type: ignore[import-untyped]
    OptimizationResult,
    RequirementAssessment,
    RequirementEvidence,
    RequirementReference,
)

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
_REQUIREMENT_CATEGORY_MAP: Mapping[str, ResumeRequirementCategory] = {
    "core_skill": ResumeRequirementCategory.CORE_SKILL,
    "preferred_skill": ResumeRequirementCategory.PREFERRED_SKILL,
    "experience": ResumeRequirementCategory.EXPERIENCE,
    "responsibility": ResumeRequirementCategory.RESPONSIBILITY,
    "education_or_qualification": (
        ResumeRequirementCategory.EDUCATION_OR_QUALIFICATION
    ),
    "keyword": ResumeRequirementCategory.KEYWORD,
}
_REQUIREMENT_IMPORTANCE_MAP: Mapping[str, ResumeRequirementImportance] = {
    "required": ResumeRequirementImportance.REQUIRED,
    "preferred": ResumeRequirementImportance.PREFERRED,
    "contextual": ResumeRequirementImportance.CONTEXTUAL,
}
_EVIDENCE_KIND_MAP: Mapping[str, ResumeEvidenceKind] = {
    "paragraph": ResumeEvidenceKind.PARAGRAPH,
    "heading": ResumeEvidenceKind.HEADING,
    "list_item": ResumeEvidenceKind.LIST_ITEM,
    "table_row": ResumeEvidenceKind.TABLE_ROW,
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


def _map_requirement_reference(
    reference: RequirementReference,
) -> ResumeRequirementReference:
    return ResumeRequirementReference(
        requirement_id=reference.requirement_id,
        description=reference.description,
        category=_map_enum_value(
            reference.category,
            _REQUIREMENT_CATEGORY_MAP,
            "requirement category",
        ),
        importance=_map_enum_value(
            reference.importance,
            _REQUIREMENT_IMPORTANCE_MAP,
            "requirement importance",
        ),
        source_excerpt=reference.source_excerpt,
    )


def _map_requirement_evidence(
    evidence: RequirementEvidence,
) -> ResumeRequirementEvidence:
    return ResumeRequirementEvidence(
        source_block_id=evidence.source_block_id,
        kind=_map_enum_value(
            evidence.kind,
            _EVIDENCE_KIND_MAP,
            "evidence kind",
        ),
        location=evidence.location,
        excerpt=evidence.excerpt,
        sections=tuple(
            ResumeEvidenceSectionReference(
                section_type=_map_enum_value(
                    section.section_type,
                    _SECTION_TYPE_MAP,
                    "evidence section_type",
                ),
                title=section.title,
            )
            for section in evidence.sections
        ),
    )


def _map_requirement_assessment(
    assessment: RequirementAssessment,
) -> ResumeRequirementAssessment:
    reference = assessment.requirement
    evidence = tuple(assessment.evidence)
    source_block_ids = tuple(assessment.source_block_ids)

    if reference is None:
        if evidence:
            raise ResumeOptimizationContractError(
                "Resume Optimizer assessment evidence requires a requirement reference."
            )
        mapped_reference = None
        mapped_evidence: tuple[ResumeRequirementEvidence, ...] = ()
    else:
        if reference.requirement_id != assessment.requirement_id:
            raise ResumeOptimizationContractError(
                "Resume Optimizer requirement provenance does not match its assessment."
            )
        evidence_ids = tuple(item.source_block_id for item in evidence)
        if evidence_ids != source_block_ids:
            raise ResumeOptimizationContractError(
                "Resume Optimizer evidence provenance does not match source_block_ids."
            )
        mapped_reference = _map_requirement_reference(reference)
        mapped_evidence = tuple(_map_requirement_evidence(item) for item in evidence)

    return ResumeRequirementAssessment(
        requirement_id=assessment.requirement_id,
        status=_map_enum_value(
            assessment.status,
            _ASSESSMENT_STATUS_MAP,
            "assessment status",
        ),
        source_block_ids=source_block_ids,
        reason=assessment.reason,
        suggested_action=assessment.suggested_action,
        requirement=mapped_reference,
        evidence=mapped_evidence,
    )


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
                _map_requirement_assessment(assessment)
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
