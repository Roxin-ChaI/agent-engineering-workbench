"use client";

import { type ChangeEvent, type FormEvent, useRef, useState } from "react";

import { usePreferences } from "@/components/preferences-provider";
import { optimizeResume } from "@/lib/api";
import type {
  ResumeAssessmentStatus,
  ResumeMatchRating,
  ResumeOptimizationResult,
  ResumeSectionType,
} from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";

const MAX_RESUME_BYTES = 10 * 1024 * 1024;
const MAX_JOB_DESCRIPTION_CHARACTERS = 30_000;
const SUPPORTED_RESUME_EXTENSIONS = new Set([".pdf", ".docx"]);

const ratingLabelKeys: Record<ResumeMatchRating, TranslationKey> = {
  high: "resume.ratingHigh",
  medium: "resume.ratingMedium",
  low: "resume.ratingLow",
};

const ratingStyles: Record<ResumeMatchRating, string> = {
  high: "status-completed",
  medium: "status-stopped",
  low: "status-failed",
};

const assessmentLabelKeys: Record<ResumeAssessmentStatus, TranslationKey> = {
  well_supported: "resume.statusWellSupported",
  underrepresented: "resume.statusUnderrepresented",
  unsupported: "resume.statusUnsupported",
};

const assessmentStyles: Record<ResumeAssessmentStatus, string> = {
  well_supported: "status-completed",
  underrepresented: "status-stopped",
  unsupported: "status-failed",
};

const sectionLabelKeys: Record<ResumeSectionType, TranslationKey> = {
  basic_info: "resume.sectionBasicInfo",
  summary: "resume.sectionSummary",
  skills: "resume.sectionSkills",
  experience: "resume.sectionExperience",
  projects: "resume.sectionProjects",
  education: "resume.sectionEducation",
  certifications: "resume.sectionCertifications",
  other: "resume.sectionOther",
};

type ValidationError =
  | "fileRequired"
  | "unsupportedFile"
  | "fileTooLarge"
  | "jobDescriptionRequired"
  | "jobDescriptionTooLong";

const validationLabelKeys: Record<ValidationError, TranslationKey> = {
  fileRequired: "resume.fileRequired",
  unsupportedFile: "resume.unsupportedFile",
  fileTooLarge: "resume.fileTooLarge",
  jobDescriptionRequired: "resume.jobDescriptionRequired",
  jobDescriptionTooLong: "resume.jobDescriptionTooLong",
};

function fileExtension(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex < 0 ? "" : filename.slice(dotIndex).toLowerCase();
}

function formatFileSize(size: number): string {
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KiB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MiB`;
}

function errorStatus(error: unknown): string | null {
  if (!(error instanceof Error)) {
    return null;
  }
  return error.message.match(/status (\d{3})/)?.[1] ?? null;
}

function StringListPanel({
  titleKey,
  emptyKey,
  items,
}: {
  titleKey: TranslationKey;
  emptyKey: TranslationKey;
  items: string[];
}) {
  const { t } = usePreferences();

  return (
    <section className="panel min-w-0">
      <h2 className="panel-title mt-0">{t(titleKey)}</h2>
      {items.length ? (
        <ul className="source-list mt-4">
          {items.map((item, index) => (
            <li
              key={`${index}-${item}`}
              className="text-secondary py-3 first:pt-0 last:pb-0 whitespace-pre-wrap break-words text-sm leading-6"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted mt-4 text-sm">{t(emptyKey)}</p>
      )}
    </section>
  );
}

export function ResumeOptimizationWorkspace() {
  const { t } = usePreferences();
  const [resume, setResume] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState<ResumeOptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] =
    useState<ValidationError | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const inFlight = useRef(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setResume(event.target.files?.[0] ?? null);
    setValidationError(null);
    setRequestError(null);
  }

  function validate(): ValidationError | null {
    if (!resume) {
      return "fileRequired";
    }
    if (!SUPPORTED_RESUME_EXTENSIONS.has(fileExtension(resume.name))) {
      return "unsupportedFile";
    }
    if (resume.size > MAX_RESUME_BYTES) {
      return "fileTooLarge";
    }
    if (!jobDescription.trim()) {
      return "jobDescriptionRequired";
    }
    if (jobDescription.length > MAX_JOB_DESCRIPTION_CHARACTERS) {
      return "jobDescriptionTooLong";
    }
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || inFlight.current) {
      return;
    }

    setValidationError(null);
    setRequestError(null);
    setResult(null);

    const nextValidationError = validate();
    if (nextValidationError) {
      setValidationError(nextValidationError);
      return;
    }

    const selectedResume = resume;
    if (!selectedResume) {
      setValidationError("fileRequired");
      return;
    }

    inFlight.current = true;
    setLoading(true);
    try {
      setResult(await optimizeResume(selectedResume, jobDescription));
    } catch (error) {
      const status = errorStatus(error);
      setRequestError(
        status ? `${t("resume.requestError")} (HTTP ${status})` : t("resume.requestError"),
      );
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }

  const displayedError = validationError
    ? t(validationLabelKeys[validationError])
    : requestError;

  return (
    <section className="mx-auto max-w-7xl">
      <p className="section-label">{t("resume.section")}</p>
      <h1 className="page-title">{t("resume.title")}</h1>
      <p className="page-description">{t("resume.description")}</p>

      <form className="panel mt-8" aria-busy={loading} onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="min-w-0">
            <label
              htmlFor="resume-file"
              className="text-primary block text-sm font-medium"
            >
              {t("resume.fileLabel")}
            </label>
            <p className="text-muted mt-1 text-xs leading-5">
              {t("resume.fileHint")}
            </p>
            <input
              id="resume-file"
              type="file"
              accept=".pdf,.docx"
              disabled={loading}
              onChange={handleFileChange}
              className="workbench-input mt-3 block w-full rounded-md border px-3 py-3 text-sm file:mr-3 file:rounded file:border-0 file:bg-[var(--accent-soft)] file:px-3 file:py-2 file:text-xs file:font-medium file:text-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
            />
            {resume ? (
              <dl className="metric-card mt-3 grid min-w-0 gap-3 rounded-md p-3 sm:grid-cols-2">
                <div className="min-w-0">
                  <dt className="text-muted text-xs">
                    {t("resume.selectedFile")}
                  </dt>
                  <dd className="text-secondary mt-1 truncate text-sm" title={resume.name}>
                    {resume.name}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted text-xs">{t("resume.fileSize")}</dt>
                  <dd className="text-secondary mt-1 font-mono text-sm">
                    {formatFileSize(resume.size)}
                  </dd>
                </div>
              </dl>
            ) : null}
          </div>

          <div className="min-w-0">
            <label
              htmlFor="resume-job-description"
              className="text-primary block text-sm font-medium"
            >
              {t("resume.jobDescription")}
            </label>
            <textarea
              id="resume-job-description"
              rows={9}
              disabled={loading}
              value={jobDescription}
              onChange={(event) => {
                setJobDescription(event.target.value);
                setValidationError(null);
                setRequestError(null);
              }}
              placeholder={t("resume.jobDescriptionPlaceholder")}
              className="workbench-input mt-3 w-full resize-y rounded-md border px-4 py-3 text-sm leading-6 outline-none disabled:cursor-not-allowed disabled:opacity-60"
            />
            <p className="text-muted mt-2 text-right font-mono text-xs">
              {t("resume.characterCount")}: {jobDescription.length.toLocaleString()} / 30,000
            </p>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between [border-color:var(--border)]">
          <div className="text-sm" aria-live="polite">
            {displayedError ? <p className="text-error">{displayedError}</p> : null}
            {loading ? <p className="text-accent">{t("resume.optimizing")}</p> : null}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="primary-action shrink-0 rounded-md border px-4 py-3 text-sm font-medium"
          >
            {loading ? t("resume.optimizing") : t("resume.optimize")}
          </button>
        </div>

        <p className="text-muted mt-4 text-xs leading-5">
          {t("resume.privacyNotice")}
        </p>
      </form>

      {result ? (
        <div className="mt-4 space-y-4">
          <section className="panel" aria-labelledby="resume-overall-heading">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="panel-kicker">{t("resume.result")}</p>
                <h2 id="resume-overall-heading" className="panel-title">
                  {t("resume.overallEvaluation")}
                </h2>
              </div>
              <span
                className={`rounded-md border px-3 py-1 font-mono text-xs ${ratingStyles[result.analysis.overall_rating]}`}
              >
                {t(ratingLabelKeys[result.analysis.overall_rating])}
              </span>
            </div>
            <p className="text-secondary mt-4 whitespace-pre-wrap break-words text-sm leading-7">
              {result.analysis.overall_evaluation}
            </p>
          </section>

          <section className="panel" aria-labelledby="resume-assessments-heading">
            <h2 id="resume-assessments-heading" className="panel-title mt-0">
              {t("resume.assessments")}
            </h2>
            {result.analysis.assessments.length ? (
              <ol className="mt-4 space-y-3">
                {result.analysis.assessments.map((assessment, index) => (
                  <li
                    key={`${index}-${assessment.requirement_id}`}
                    className="metric-card min-w-0 rounded-md p-4 sm:p-5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-muted text-xs">
                          {t("resume.requirement")}
                        </p>
                        <p className="text-primary mt-1 break-words font-mono text-sm font-semibold">
                          {assessment.requirement_id}
                        </p>
                      </div>
                      <span
                        className={`rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${assessmentStyles[assessment.status]}`}
                      >
                        {t(assessmentLabelKeys[assessment.status])}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <div>
                        <h3 className="text-primary text-xs font-semibold uppercase tracking-wider">
                          {t("resume.reason")}
                        </h3>
                        <p className="text-secondary mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                          {assessment.reason}
                        </p>
                      </div>
                      <div>
                        <h3 className="text-primary text-xs font-semibold uppercase tracking-wider">
                          {t("resume.suggestedAction")}
                        </h3>
                        <p className="text-secondary mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                          {assessment.suggested_action}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4">
                      <h3 className="text-primary text-xs font-semibold uppercase tracking-wider">
                        {t("resume.sourceBlocks")}
                      </h3>
                      <p className="text-muted mt-2 break-words font-mono text-xs leading-5">
                        {assessment.source_block_ids.length
                          ? assessment.source_block_ids.join(", ")
                          : t("resume.noSourceBlocks")}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-muted mt-4 text-sm">{t("resume.noAssessments")}</p>
            )}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <StringListPanel
              titleKey="resume.mainIssues"
              emptyKey="resume.noMainIssues"
              items={result.analysis.main_issues}
            />
            <StringListPanel
              titleKey="resume.sectionSuggestions"
              emptyKey="resume.noSectionSuggestions"
              items={result.analysis.section_suggestions}
            />
            <StringListPanel
              titleKey="resume.keywordSuggestions"
              emptyKey="resume.noKeywordSuggestions"
              items={result.analysis.keyword_suggestions}
            />
            <StringListPanel
              titleKey="resume.truthfulnessRisks"
              emptyKey="resume.noTruthfulnessRisks"
              items={result.analysis.truthfulness_risks}
            />
            <StringListPanel
              titleKey="resume.contentNotToAdd"
              emptyKey="resume.noContentNotToAdd"
              items={result.analysis.content_not_to_add}
            />
            <StringListPanel
              titleKey="resume.pendingUserInputs"
              emptyKey="resume.noPendingUserInputs"
              items={result.optimized_resume.pending_user_inputs}
            />
          </div>

          <section className="panel" aria-labelledby="optimized-resume-heading">
            <h2 id="optimized-resume-heading" className="panel-title mt-0">
              {t("resume.optimizedResume")}
            </h2>
            {result.optimized_resume.sections.length ? (
              <div className="mt-4 space-y-4">
                {result.optimized_resume.sections.map((section, sectionIndex) => (
                  <section
                    key={`${sectionIndex}-${section.section_type}-${section.title}`}
                    className="metric-card min-w-0 rounded-md p-4 sm:p-5"
                  >
                    <p className="text-accent font-mono text-[10px] uppercase tracking-wider">
                      {t(sectionLabelKeys[section.section_type])}
                    </p>
                    <h3 className="text-primary mt-2 break-words text-base font-semibold">
                      {section.title}
                    </h3>
                    <p className="text-muted mt-2 break-words font-mono text-xs leading-5">
                      {t("resume.sourceBlocks")}: {section.source_block_ids.length
                        ? section.source_block_ids.join(", ")
                        : t("resume.noSourceBlocks")}
                    </p>
                    {section.items.length ? (
                      <ol className="source-list mt-4">
                        {section.items.map((item, itemIndex) => (
                          <li
                            key={`${itemIndex}-${item.text}`}
                            className="py-4 first:pt-0 last:pb-0"
                          >
                            <p className="text-secondary whitespace-pre-wrap break-words text-sm leading-7">
                              {item.text}
                            </p>
                            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                              <div className="min-w-0">
                                <dt className="text-muted text-xs">
                                  {t("resume.sourceBlocks")}
                                </dt>
                                <dd className="text-muted mt-1 break-words font-mono text-xs leading-5">
                                  {item.source_block_ids.length
                                    ? item.source_block_ids.join(", ")
                                    : t("resume.noSourceBlocks")}
                                </dd>
                              </div>
                              <div className="min-w-0">
                                <dt className="text-muted text-xs">
                                  {t("resume.relatedRequirements")}
                                </dt>
                                <dd className="text-muted mt-1 break-words font-mono text-xs leading-5">
                                  {item.related_requirement_ids.length
                                    ? item.related_requirement_ids.join(", ")
                                    : t("resume.noRelatedRequirements")}
                                </dd>
                              </div>
                            </dl>
                            {item.needs_review || item.review_note ? (
                              <div className="status-stopped mt-3 rounded-md border p-3">
                                <p className="font-mono text-[10px] uppercase tracking-wider">
                                  {t("resume.needsReview")}
                                </p>
                                {item.review_note ? (
                                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                                    {item.review_note}
                                  </p>
                                ) : null}
                              </div>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="text-muted mt-4 text-sm">
                        {t("resume.noSectionItems")}
                      </p>
                    )}
                  </section>
                ))}
              </div>
            ) : (
              <p className="text-muted mt-4 text-sm">{t("resume.noResumeSections")}</p>
            )}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <StringListPanel
              titleKey="resume.optimizedResumeWarnings"
              emptyKey="resume.noOptimizedResumeWarnings"
              items={result.optimized_resume.warnings}
            />
            <StringListPanel
              titleKey="resume.resultWarnings"
              emptyKey="resume.noResultWarnings"
              items={result.warnings}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
