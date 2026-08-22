from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _ImmutableResumeContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResumeMatchRating(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResumeAssessmentStatus(StrEnum):
    WELL_SUPPORTED = "well_supported"
    UNDERREPRESENTED = "underrepresented"
    UNSUPPORTED = "unsupported"


class ResumeSectionType(StrEnum):
    BASIC_INFO = "basic_info"
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    OTHER = "other"


class ResumeRequirementAssessment(_ImmutableResumeContract):
    requirement_id: str
    status: ResumeAssessmentStatus
    source_block_ids: tuple[str, ...]
    reason: str
    suggested_action: str


class ResumeMatchAnalysis(_ImmutableResumeContract):
    overall_rating: ResumeMatchRating
    overall_evaluation: str
    assessments: tuple[ResumeRequirementAssessment, ...]
    main_issues: tuple[str, ...]
    section_suggestions: tuple[str, ...]
    keyword_suggestions: tuple[str, ...]
    truthfulness_risks: tuple[str, ...]
    content_not_to_add: tuple[str, ...]


class ResumeOptimizationItem(_ImmutableResumeContract):
    text: str
    source_block_ids: tuple[str, ...]
    related_requirement_ids: tuple[str, ...]
    needs_review: bool
    review_note: str | None


class ResumeOptimizationSection(_ImmutableResumeContract):
    section_type: ResumeSectionType
    title: str
    items: tuple[ResumeOptimizationItem, ...]
    source_block_ids: tuple[str, ...]


class OptimizedResume(_ImmutableResumeContract):
    sections: tuple[ResumeOptimizationSection, ...]
    pending_user_inputs: tuple[str, ...]
    warnings: tuple[str, ...]


class ResumeOptimizationResult(_ImmutableResumeContract):
    analysis: ResumeMatchAnalysis
    optimized_resume: OptimizedResume
    warnings: tuple[str, ...]
