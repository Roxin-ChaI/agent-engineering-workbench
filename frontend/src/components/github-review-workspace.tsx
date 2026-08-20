"use client";

import { type FormEvent, useRef, useState } from "react";

import { usePreferences } from "@/components/preferences-provider";
import { reviewPullRequest } from "@/lib/api";
import type {
  GitHubReviewFinding,
  GitHubReviewResult,
  GitHubReviewSeverity,
} from "@/lib/contracts";

const severityStyles: Record<GitHubReviewSeverity, string> = {
  Critical: "status-failed",
  High: "status-failed",
  Medium: "status-stopped",
  Low: "status-running",
};

function FindingCard({
  finding,
  index,
}: {
  finding: GitHubReviewFinding;
  index: number;
}) {
  const { t } = usePreferences();

  return (
    <li className="metric-card min-w-0 rounded-md p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-muted font-mono text-[10px] uppercase tracking-wider">
            {t("githubReview.findingNumber")} #{index + 1}
          </p>
          <p className="text-muted mt-2 text-xs">
            {t("githubReview.issue")}
          </p>
          <p className="text-primary mt-1 text-sm font-semibold leading-6">
            {finding.issue}
          </p>
        </div>
        <span
          aria-label={`${t("githubReview.severity")}: ${finding.severity}`}
          className={`shrink-0 rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${severityStyles[finding.severity]}`}
        >
          {finding.severity}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="min-w-0">
          <dt className="text-muted text-xs">{t("githubReview.file")}</dt>
          <dd className="text-secondary mt-1 break-all font-mono text-xs">
            {finding.file_path}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-muted text-xs">
            {t("githubReview.location")}
          </dt>
          <dd className="text-secondary mt-1 break-words font-mono text-xs">
            {finding.location}
          </dd>
        </div>
      </dl>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-primary text-xs font-semibold uppercase tracking-wider">
            {t("githubReview.evidence")}
          </h3>
          <p className="text-secondary mt-2 whitespace-pre-wrap break-words text-sm leading-6">
            {finding.evidence}
          </p>
        </div>
        <div>
          <h3 className="text-primary text-xs font-semibold uppercase tracking-wider">
            {t("githubReview.recommendation")}
          </h3>
          <p className="text-secondary mt-2 whitespace-pre-wrap break-words text-sm leading-6">
            {finding.recommendation}
          </p>
        </div>
      </div>
    </li>
  );
}

export function GitHubReviewWorkspace() {
  const { t } = usePreferences();
  const [prUrl, setPrUrl] = useState("");
  const [result, setResult] = useState<GitHubReviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || inFlight.current) {
      return;
    }

    const normalizedPrUrl = prUrl.trim();
    if (!normalizedPrUrl) {
      setError(t("githubReview.emptyUrl"));
      return;
    }

    inFlight.current = true;
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      setResult(await reviewPullRequest(normalizedPrUrl));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : t("githubReview.error"),
      );
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }

  const overview = result
    ? [
        [
          t("githubReview.repository"),
          `${result.target.owner}/${result.target.repository}`,
        ],
        [t("githubReview.prNumber"), `#${result.target.pull_number}`],
        [t("githubReview.titleLabel"), result.pull_request.title],
        [t("githubReview.state"), result.pull_request.state],
        [t("githubReview.author"), result.pull_request.author],
        [
          t("githubReview.branches"),
          `${result.pull_request.base_branch} → ${result.pull_request.head_branch}`,
        ],
        [
          t("githubReview.changedFiles"),
          String(result.pull_request.changed_files),
        ],
        [t("githubReview.additions"), String(result.pull_request.additions)],
        [t("githubReview.deletions"), String(result.pull_request.deletions)],
        [t("githubReview.commits"), String(result.pull_request.commits)],
        [t("githubReview.created"), result.pull_request.created_at],
        [t("githubReview.updated"), result.pull_request.updated_at],
      ]
    : [];

  return (
    <section className="mx-auto max-w-7xl">
      <p className="section-label">{t("githubReview.section")}</p>
      <h1 className="page-title">{t("githubReview.title")}</h1>
      <p className="page-description">{t("githubReview.description")}</p>

      <form className="panel mt-8" aria-busy={loading} onSubmit={handleSubmit}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="min-w-0 flex-1">
            <label
              htmlFor="github-pr-url"
              className="text-primary block text-sm font-medium"
            >
              {t("githubReview.prUrl")}
            </label>
            <input
              id="github-pr-url"
              type="text"
              inputMode="url"
              autoComplete="url"
              value={prUrl}
              onChange={(event) => setPrUrl(event.target.value)}
              placeholder="https://github.com/owner/repository/pull/123"
              className="workbench-input mt-2 w-full rounded-md border px-4 py-3 font-mono text-sm outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="primary-action shrink-0 rounded-md border px-4 py-3 text-sm font-medium"
          >
            {loading
              ? t("githubReview.reviewing")
              : t("githubReview.run")}
          </button>
        </div>

        <div className="mt-4 text-sm" aria-live="polite">
          {error ? <p className="text-error">{error}</p> : null}
          {loading ? (
            <p className="text-accent">{t("githubReview.reviewing")}</p>
          ) : null}
        </div>

        <p className="text-muted mt-4 border-t pt-4 text-xs leading-5 [border-color:var(--border)]">
          {t("githubReview.readOnlyNotice")}
        </p>
      </form>

      {result ? (
        <div className="mt-4 space-y-4">
          <section className="panel" aria-labelledby="pr-overview-heading">
            <h2 id="pr-overview-heading" className="panel-title mt-0">
              {t("githubReview.overview")}
            </h2>
            <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {overview.map(([label, value]) => (
                <div key={label} className="metric-card min-w-0 rounded-md p-3">
                  <dt className="text-muted text-[11px]">{label}</dt>
                  <dd className="text-secondary mt-2 break-words font-mono text-xs leading-5">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.6fr)]">
            <section className="panel min-w-0" aria-labelledby="summary-heading">
              <h2 id="summary-heading" className="panel-title mt-0">
                {t("githubReview.summary")}
              </h2>
              <p className="text-secondary mt-4 whitespace-pre-wrap break-words text-sm leading-7">
                {result.summary}
              </p>
            </section>

            <section className="panel min-w-0" aria-labelledby="assessment-heading">
              <h2 id="assessment-heading" className="panel-title mt-0">
                {t("githubReview.assessment")}
              </h2>
              <p className="text-accent mt-4 break-words font-mono text-sm">
                {result.assessment}
              </p>
            </section>
          </div>

          <section className="panel" aria-labelledby="findings-heading">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="findings-heading" className="panel-title mt-0">
                {t("githubReview.findings")}
              </h2>
              <span className="text-muted font-mono text-xs">
                {result.findings.length}
              </span>
            </div>
            {result.findings.length ? (
              <ol className="mt-5 space-y-3">
                {result.findings.map((finding, index) => (
                  <FindingCard
                    key={`${index}-${finding.file_path}-${finding.location}`}
                    finding={finding}
                    index={index}
                  />
                ))}
              </ol>
            ) : (
              <p className="text-muted mt-5 text-sm">
                {t("githubReview.noFindings")}
              </p>
            )}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="panel min-w-0" aria-labelledby="test-gaps-heading">
              <h2 id="test-gaps-heading" className="panel-title mt-0">
                {t("githubReview.testGaps")}
              </h2>
              <p className="text-secondary mt-4 whitespace-pre-wrap break-words text-sm leading-7">
                {result.test_gaps}
              </p>
            </section>
            <section
              className="panel min-w-0"
              aria-labelledby="maintainability-heading"
            >
              <h2 id="maintainability-heading" className="panel-title mt-0">
                {t("githubReview.maintainability")}
              </h2>
              <p className="text-secondary mt-4 whitespace-pre-wrap break-words text-sm leading-7">
                {result.maintainability}
              </p>
            </section>
          </div>

          <section className="panel min-w-0" aria-labelledby="markdown-heading">
            <h2 id="markdown-heading" className="panel-title mt-0">
              {t("githubReview.markdown")}
            </h2>
            <pre className="metric-card text-secondary mt-4 max-w-full overflow-x-auto rounded-md p-4 whitespace-pre-wrap break-words font-mono text-xs leading-6">
              {result.markdown}
            </pre>
          </section>
        </div>
      ) : null}
    </section>
  );
}
