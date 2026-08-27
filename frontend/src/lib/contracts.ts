export type RunStatus = "completed" | "failed" | "stopped";

export interface TraceEvent {
  sequence: number;
  event_type: string;
  name: string;
  detail: string | null;
}

export interface RunMetrics {
  iterations: number | null;
  tool_calls: number | null;
  duration_ms: number | null;
}

export interface SourceReference {
  title: string;
  url: string | null;
}

export interface RunResult {
  status: RunStatus;
  output: string | null;
  trace: TraceEvent[];
  metrics: RunMetrics;
  sources: SourceReference[];
  error: string | null;
}

export interface WebResearchRequest {
  query: string;
}

export type StreamEventType =
  | "started"
  | "trace"
  | "completed"
  | "stopped"
  | "error";

export interface StreamEvent {
  sequence: number;
  event_type: StreamEventType;
  data: Record<string, unknown>;
}

export type ContextMessageRole = "system" | "user" | "assistant" | "tool";

export interface ContextMessage {
  role: ContextMessageRole;
  content: string | null;
}

export type ContextCompressionStrategy =
  | "no_compression"
  | "truncation"
  | "windowed";

export interface ContextCompressionInput {
  messages: ContextMessage[];
  target_token_budget: number;
  max_token_budget: number;
  strategy: ContextCompressionStrategy;
}

export interface ContextCompressionResult {
  original_messages: ContextMessage[];
  compressed_messages: ContextMessage[];
  original_token_estimate: number;
  compressed_token_estimate: number;
  tokens_saved_estimate: number;
  compression_ratio: number;
  strategy: ContextCompressionStrategy;
  duration_ms: number;
  compression_applied: boolean;
  compressed_message_count: number;
  preserved_message_count: number;
}

export interface GitHubReviewRequest {
  pr_url: string;
}

export interface GitHubReviewTarget {
  owner: string;
  repository: string;
  pull_number: number;
}

export interface GitHubPullRequestMetadata {
  title: string;
  state: string;
  author: string;
  base_branch: string;
  head_branch: string;
  created_at: string;
  updated_at: string;
  changed_files: number;
  additions: number;
  deletions: number;
  commits: number;
}

export type GitHubReviewSeverity = "Critical" | "High" | "Medium" | "Low";

export interface GitHubReviewFinding {
  severity: GitHubReviewSeverity;
  file_path: string;
  location: string;
  issue: string;
  evidence: string;
  recommendation: string;
}

export type GitHubReviewAssessment =
  | "Approve"
  | "Approve with minor comments"
  | "Request changes"
  | "Insufficient data";

export interface GitHubReviewResult {
  target: GitHubReviewTarget;
  pull_request: GitHubPullRequestMetadata;
  summary: string;
  findings: GitHubReviewFinding[];
  test_gaps: string;
  maintainability: string;
  assessment: GitHubReviewAssessment;
  markdown: string;
}

export type ResumeMatchRating = "high" | "medium" | "low";

export type ResumeAssessmentStatus =
  | "well_supported"
  | "underrepresented"
  | "unsupported";

export type ResumeRequirementCategory =
  | "core_skill"
  | "preferred_skill"
  | "experience"
  | "responsibility"
  | "education_or_qualification"
  | "keyword";

export type ResumeRequirementImportance =
  | "required"
  | "preferred"
  | "contextual";

export type ResumeEvidenceKind =
  | "paragraph"
  | "heading"
  | "list_item"
  | "table_row";

export type ResumeSectionType =
  | "basic_info"
  | "summary"
  | "skills"
  | "experience"
  | "projects"
  | "education"
  | "certifications"
  | "other";

export interface ResumeRequirementReference {
  requirement_id: string;
  description: string;
  category: ResumeRequirementCategory;
  importance: ResumeRequirementImportance;
  source_excerpt: string;
}

export interface ResumeEvidenceSectionReference {
  section_type: ResumeSectionType;
  title: string;
}

export interface ResumeRequirementEvidence {
  source_block_id: string;
  kind: ResumeEvidenceKind;
  location: string;
  excerpt: string;
  sections: ResumeEvidenceSectionReference[];
}

export interface ResumeRequirementAssessment {
  requirement_id: string;
  status: ResumeAssessmentStatus;
  source_block_ids: string[];
  reason: string;
  suggested_action: string;
  requirement?: ResumeRequirementReference | null;
  evidence?: ResumeRequirementEvidence[];
}

export interface ResumeMatchAnalysis {
  overall_rating: ResumeMatchRating;
  overall_evaluation: string;
  assessments: ResumeRequirementAssessment[];
  main_issues: string[];
  section_suggestions: string[];
  keyword_suggestions: string[];
  truthfulness_risks: string[];
  content_not_to_add: string[];
}

export interface ResumeOptimizationItem {
  text: string;
  source_block_ids: string[];
  related_requirement_ids: string[];
  needs_review: boolean;
  review_note: string | null;
}

export interface ResumeOptimizationSection {
  section_type: ResumeSectionType;
  title: string;
  items: ResumeOptimizationItem[];
  source_block_ids: string[];
}

export interface OptimizedResume {
  sections: ResumeOptimizationSection[];
  pending_user_inputs: string[];
  warnings: string[];
}

export interface ResumeOptimizationResult {
  analysis: ResumeMatchAnalysis;
  optimized_resume: OptimizedResume;
  warnings: string[];
}

export const PROMPT_EXPERIMENT_VARIANTS = [
  "baseline",
  "tone_trump",
  "tone_casual",
  "wiki_random",
  "no_tool_desc",
  "all_ablations",
] as const;

export type PromptExperimentVariant =
  (typeof PROMPT_EXPERIMENT_VARIANTS)[number];

export type PromptExperimentEnvironment = "airline" | "retail";

export interface PromptBundleInput {
  system_prompt: string;
  wiki_rules: string[];
}

export interface PromptSuccessCriteria {
  require_final_response?: boolean;
  exact_response?: string | null;
  required_response_substrings?: string[];
  forbidden_response_substrings?: string[];
  required_tool_names?: string[];
  forbidden_tool_names?: string[];
}

export interface PromptTaskInput {
  task_id: string;
  environment: PromptExperimentEnvironment;
  instruction: string;
  success_criteria?: PromptSuccessCriteria;
}

export interface PromptExperimentOptions {
  max_steps?: number;
  seed?: number;
}

export interface PromptExperimentRequest {
  prompt: PromptBundleInput;
  task: PromptTaskInput;
  variant?: PromptExperimentVariant;
  options?: PromptExperimentOptions;
}

export interface PromptEvaluationSummary {
  reward: number;
  completed: boolean;
  criteria_total: number;
  criteria_passed: number;
  criteria_failed: number;
}

export interface PromptExperimentMetrics {
  step_count: number;
  tool_call_count: number;
}

export interface PromptExperimentResult {
  task_id: string;
  variant: PromptExperimentVariant;
  final_response: string | null;
  reward: number;
  completed: boolean;
  evaluation: PromptEvaluationSummary;
  metrics: PromptExperimentMetrics;
}
