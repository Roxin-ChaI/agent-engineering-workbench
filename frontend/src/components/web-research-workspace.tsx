"use client";

import { type FormEvent, useRef, useState } from "react";

import { usePreferences } from "@/components/preferences-provider";
import {
  streamKnowledgeResearch,
  streamWebResearch,
} from "@/lib/api";
import type {
  RunResult,
  RunStatus,
  StreamEvent,
  TraceEvent,
} from "@/lib/contracts";

type DisplayStatus = RunStatus | "running";
type ResearchWorkspaceKind = "web" | "knowledge";

const statusStyles: Record<DisplayStatus, string> = {
  running: "status-running",
  completed: "status-completed",
  stopped: "status-stopped",
  failed: "status-failed",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || typeof value === "number";
}

function isRunStatus(value: unknown): value is RunStatus {
  return value === "completed" || value === "stopped" || value === "failed";
}

function isTraceEvent(value: unknown): value is TraceEvent {
  return (
    isRecord(value) &&
    typeof value.sequence === "number" &&
    Number.isInteger(value.sequence) &&
    value.sequence >= 0 &&
    typeof value.event_type === "string" &&
    typeof value.name === "string" &&
    isNullableString(value.detail)
  );
}

function isRunResult(value: unknown): value is RunResult {
  if (
    !isRecord(value) ||
    !isRunStatus(value.status) ||
    !isNullableString(value.output) ||
    !Array.isArray(value.trace) ||
    !value.trace.every(isTraceEvent) ||
    !isRecord(value.metrics) ||
    !isNullableNumber(value.metrics.iterations) ||
    !isNullableNumber(value.metrics.tool_calls) ||
    !isNullableNumber(value.metrics.duration_ms) ||
    !Array.isArray(value.sources) ||
    !isNullableString(value.error)
  ) {
    return false;
  }

  return value.sources.every(
    (source) =>
      isRecord(source) &&
      typeof source.title === "string" &&
      isNullableString(source.url),
  );
}

function getTerminalResult(
  event: StreamEvent,
  expectedStatus: RunStatus,
): RunResult {
  if (!isRunResult(event.data) || event.data.status !== expectedStatus) {
    throw new Error("Invalid terminal web research stream event");
  }
  return event.data;
}

function formatMetric(value: number | null, suffix = ""): string {
  return value === null ? "—" : `${value}${suffix}`;
}

function formatDuration(durationMs: number | null): string {
  if (durationMs === null) {
    return "—";
  }
  if (durationMs < 1000) {
    return `${Math.round(durationMs)} ms`;
  }
  if (durationMs < 60_000) {
    const seconds = (durationMs / 1000).toFixed(1).replace(/\.0$/, "");
    return `${seconds} s`;
  }

  const totalSeconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
}

function ResearchWorkspace({ kind }: { kind: ResearchWorkspaceKind }) {
  const { t } = usePreferences();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState(false);
  const inFlight = useRef(false);
  const isKnowledgeResearch = kind === "knowledge";
  const streamResearch = isKnowledgeResearch
    ? streamKnowledgeResearch
    : streamWebResearch;
  const safeFailureMessage = isKnowledgeResearch
    ? "knowledge research execution failed"
    : "web research execution failed";

  const canSubmit = query.trim().length > 0 && !loading;
  const displayedStatus: DisplayStatus | null = loading
    ? "running"
    : (result?.status ?? null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || inFlight.current) {
      return;
    }

    inFlight.current = true;
    setResult(null);
    setTrace([]);
    setError(false);
    setStarted(false);
    setLoading(true);

    let terminalReceived = false;
    const seenTraceSequences = new Set<number>();

    try {
      await streamResearch(query, (streamEvent) => {
        if (terminalReceived) {
          return;
        }

        switch (streamEvent.event_type) {
          case "started":
            if (streamEvent.data.status !== "started") {
              throw new Error("Invalid started research stream event");
            }
            setStarted(true);
            break;
          case "trace":
            if (!isTraceEvent(streamEvent.data)) {
              throw new Error("Invalid trace research stream event");
            }
            const traceEvent = streamEvent.data;
            if (!seenTraceSequences.has(streamEvent.sequence)) {
              seenTraceSequences.add(streamEvent.sequence);
              setTrace((currentTrace) => [...currentTrace, traceEvent]);
            }
            break;
          case "completed":
            terminalReceived = true;
            setResult(getTerminalResult(streamEvent, "completed"));
            break;
          case "stopped":
            terminalReceived = true;
            setResult(getTerminalResult(streamEvent, "stopped"));
            break;
          case "error":
            terminalReceived = true;
            if (isRunResult(streamEvent.data) && streamEvent.data.status === "failed") {
              setResult(streamEvent.data);
            } else if (streamEvent.data.message === safeFailureMessage) {
              setError(true);
            } else {
              throw new Error("Invalid error research stream event");
            }
            break;
        }
      });

      if (!terminalReceived) {
        throw new Error("Research stream ended without a terminal event");
      }
    } catch {
      setError(true);
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }

  const statusLabels: Record<DisplayStatus, string> = {
    running: t("status.running"),
    completed: t("status.completed"),
    stopped: t("status.stopped"),
    failed: t("status.failed"),
  };

  return (
    <section className="mx-auto max-w-6xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="section-label">{t("research.section")}</p>
          <h1 className="page-title">
            {t(
              isKnowledgeResearch
                ? "knowledgeResearch.title"
                : "research.title",
            )}
          </h1>
          <p className="page-description">
            {t(
              isKnowledgeResearch
                ? "knowledgeResearch.description"
                : "research.description",
            )}
          </p>
        </div>
        {displayedStatus ? (
          <span
            className={`w-fit rounded-md border px-3 py-1.5 font-mono text-xs uppercase tracking-wider ${statusStyles[displayedStatus]}`}
          >
            {statusLabels[displayedStatus]}
          </span>
        ) : null}
      </div>

      <form
        className="panel mt-8"
        aria-labelledby="question-heading"
        onSubmit={handleSubmit}
      >
        <div className="flex items-center justify-between gap-4">
          <h2 id="question-heading" className="panel-title mt-0">
            {t("research.question")}
          </h2>
          <span className="text-muted font-mono text-[10px] uppercase tracking-wider">
            {t("research.sseStream")}
          </span>
        </div>
        <label htmlFor="research-question" className="sr-only">
          {t("research.questionLabel")}
        </label>
        <textarea
          id="research-question"
          rows={4}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t(
            isKnowledgeResearch
              ? "knowledgeResearch.questionPlaceholder"
              : "research.questionPlaceholder",
          )}
          className="workbench-input mt-4 w-full resize-none rounded-md border px-4 py-3 text-sm outline-none"
        />
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm" aria-live="polite">
            {error ? (
              <p className="text-error">
                {t(
                  isKnowledgeResearch
                    ? "knowledgeResearch.error"
                    : "research.error",
                )}
              </p>
            ) : null}
            {loading ? (
              <p className="text-accent">
                {started
                  ? t("research.runStarted")
                  : t("research.startingStream")}
              </p>
            ) : null}
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className="primary-action rounded-md border px-4 py-2 text-sm font-medium"
          >
            {loading ? t("research.running") : t("research.run")}
          </button>
        </div>
      </form>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.8fr)]">
        <div className="space-y-4">
          <section className="panel min-h-64" aria-labelledby="answer-heading">
            <div className="flex items-center justify-between gap-4">
              <h2 id="answer-heading" className="panel-title mt-0">
                {t("research.answer")}
              </h2>
              {result ? (
                <span className="text-muted font-mono text-[10px] uppercase tracking-wider">
                  {statusLabels[result.status]}
                </span>
              ) : null}
            </div>
            <div className="text-secondary mt-6 whitespace-pre-wrap text-sm leading-7">
              {result ? (
                result.output || t("research.noFinalAnswer")
              ) : (
                <span className="text-muted">
                  {t(
                    isKnowledgeResearch
                      ? "knowledgeResearch.answerPlaceholder"
                      : "research.answerPlaceholder",
                  )}
                </span>
              )}
            </div>
          </section>

          <section className="panel" aria-labelledby="sources-heading">
            <h2 id="sources-heading" className="panel-title mt-0">
              {t(
                isKnowledgeResearch
                  ? "knowledgeResearch.sources"
                  : "research.sources",
              )}
            </h2>
            {result?.sources.length ? (
              <ul className="source-list mt-4">
                {result.sources.map((source, index) => (
                  <li
                    key={`${source.title}-${source.url ?? index}`}
                    className="py-3 first:pt-0 last:pb-0"
                  >
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="link-accent text-sm hover:underline"
                      >
                        {source.title}
                      </a>
                    ) : (
                      <span className="text-secondary text-sm">
                        {source.title}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted mt-4 text-sm">
                {t(
                  isKnowledgeResearch
                    ? "knowledgeResearch.noSources"
                    : "research.noSources",
                )}
              </p>
            )}
          </section>
        </div>

        <div className="space-y-4">
          <section
            className="panel min-h-64"
            aria-labelledby="activity-heading"
          >
            <h2 id="activity-heading" className="panel-title mt-0">
              {t("research.activity")}
            </h2>
            <p className="text-muted mt-2 text-xs leading-5">
              {t(
                isKnowledgeResearch
                  ? "knowledgeResearch.activityNotice"
                  : "research.activityNotice",
              )}
            </p>
            {trace.length ? (
              <ol className="activity-list mt-5 space-y-4 border-l pl-4">
                {trace.map((event) => (
                  <li key={`${event.sequence}-${event.event_type}-${event.name}`}>
                    <div className="text-muted flex items-center gap-2 font-mono text-[11px]">
                      <span>#{event.sequence}</span>
                      <span>{event.event_type}</span>
                    </div>
                    <p className="text-primary mt-1 text-sm font-medium">
                      {event.name}
                    </p>
                    {event.detail ? (
                      <p className="text-muted mt-1 text-xs leading-5">
                        {event.detail}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-muted mt-5 font-mono text-xs">
                {t(
                  isKnowledgeResearch
                    ? "knowledgeResearch.noTrace"
                    : "research.noTrace",
                )}
              </p>
            )}
          </section>

          <section className="panel" aria-labelledby="metrics-heading">
            <h2 id="metrics-heading" className="panel-title mt-0">
              {t("research.metrics")}
            </h2>
            <dl className="mt-4 grid grid-cols-3 gap-3">
              {[
                [
                  t("research.iterations"),
                  formatMetric(result?.metrics.iterations ?? null),
                ],
                [
                  t("research.toolCalls"),
                  formatMetric(result?.metrics.tool_calls ?? null),
                ],
                [
                  t("research.duration"),
                  formatDuration(result?.metrics.duration_ms ?? null),
                ],
              ].map(([label, value]) => (
                <div key={label} className="metric-card rounded-md p-3">
                  <dt className="text-muted text-[11px]">{label}</dt>
                  <dd className="text-secondary mt-2 font-mono text-sm">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </div>
    </section>
  );
}

export function WebResearchWorkspace() {
  return <ResearchWorkspace kind="web" />;
}

export function KnowledgeResearchWorkspace() {
  return <ResearchWorkspace kind="knowledge" />;
}
