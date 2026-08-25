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


class ResumeRequirementCategory(StrEnum):
    CORE_SKILL = "core_skill"
    PREFERRED_SKILL = "preferred_skill"
    EXPERIENCE = "experience"
    RESPONSIBILITY = "responsibility"
    EDUCATION_OR_QUALIFICATION = "education_or_qualification"
    KEYWORD = "keyword"


class ResumeRequirementImportance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    CONTEXTUAL = "contextual"


class ResumeEvidenceKind(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE_ROW = "table_row"


class ResumeSectionType(StrEnum):
    BASIC_INFO = "basic_info"
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    OTHER = "other"


class ResumeRequirementReference(_ImmutableResumeContract):
    requirement_id: str
    description: str
    category: ResumeRequirementCategory
    importance: ResumeRequirementImportance
    source_excerpt: str


class ResumeEvidenceSectionReference(_ImmutableResumeContract):
    section_type: ResumeSectionType
    title: str


class ResumeRequirementEvidence(_ImmutableResumeContract):
    source_block_id: str
    kind: ResumeEvidenceKind
    location: str
    excerpt: str
    sections: tuple[ResumeEvidenceSectionReference, ...]


class ResumeRequirementAssessment(_ImmutableResumeContract):
    requirement_id: str
    status: ResumeAssessmentStatus
    source_block_ids: tuple[str, ...]
    reason: str
    suggested_action: str
    requirement: ResumeRequirementReference | None = None
    evidence: tuple[ResumeRequirementEvidence, ...] = ()


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
