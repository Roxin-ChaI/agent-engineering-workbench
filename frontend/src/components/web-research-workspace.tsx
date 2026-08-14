"use client";

import { type FormEvent, useState } from "react";

import { runWebResearch } from "@/lib/api";
import type { RunResult, RunStatus } from "@/lib/contracts";

const statusStyles: Record<RunStatus, string> = {
  completed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  stopped: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  failed: "border-rose-500/30 bg-rose-500/10 text-rose-300",
};

function formatMetric(value: number | null, suffix = ""): string {
  return value === null ? "—" : `${value}${suffix}`;
}

export function WebResearchWorkspace() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = query.trim().length > 0 && !loading;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const nextResult = await runWebResearch(query);
      setResult(nextResult);
    } catch {
      setError("Unable to complete web research.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-6xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="section-label">Research / Workspace</p>
          <h1 className="page-title">Web Research</h1>
          <p className="page-description">
            Run a research question and inspect the final answer, agent
            activity, metrics, and structured sources.
          </p>
        </div>
        {result ? (
          <span
            className={`w-fit rounded-md border px-3 py-1.5 font-mono text-xs uppercase tracking-wider ${statusStyles[result.status]}`}
          >
            {result.status}
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
            Question
          </h2>
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">
            REST request
          </span>
        </div>
        <label htmlFor="research-question" className="sr-only">
          Research question
        </label>
        <textarea
          id="research-question"
          rows={4}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Enter a research question..."
          className="mt-4 w-full resize-none rounded-md border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500"
        />
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-rose-300" role="alert" aria-live="polite">
            {error}
          </p>
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-md border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition-colors hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:border-slate-700 disabled:bg-slate-900 disabled:text-slate-600"
          >
            {loading ? "Running..." : "Run Research"}
          </button>
        </div>
      </form>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.8fr)]">
        <div className="space-y-4">
          <section className="panel min-h-64" aria-labelledby="answer-heading">
            <div className="flex items-center justify-between gap-4">
              <h2 id="answer-heading" className="panel-title mt-0">
                Answer
              </h2>
              {result ? (
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {result.status}
                </span>
              ) : null}
            </div>
            <div className="mt-6 whitespace-pre-wrap text-sm leading-7 text-slate-300">
              {result ? (
                result.output || "No final answer."
              ) : (
                <span className="text-slate-600">
                  The research answer will appear here after a run.
                </span>
              )}
            </div>
          </section>

          <section className="panel" aria-labelledby="sources-heading">
            <h2 id="sources-heading" className="panel-title mt-0">
              Sources
            </h2>
            {result?.sources.length ? (
              <ul className="mt-4 divide-y divide-slate-800">
                {result.sources.map((source, index) => (
                  <li key={`${source.title}-${source.url ?? index}`} className="py-3 first:pt-0 last:pb-0">
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm text-cyan-300 hover:text-cyan-200 hover:underline"
                      >
                        {source.title}
                      </a>
                    ) : (
                      <span className="text-sm text-slate-300">
                        {source.title}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-slate-600">
                No structured sources.
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
              Agent Activity
            </h2>
            {result?.trace.length ? (
              <ol className="mt-5 space-y-4 border-l border-slate-800 pl-4">
                {result.trace.map((event) => (
                  <li key={`${event.sequence}-${event.event_type}-${event.name}`}>
                    <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500">
                      <span>#{event.sequence}</span>
                      <span>{event.event_type}</span>
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-200">
                      {event.name}
                    </p>
                    {event.detail ? (
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {event.detail}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-5 font-mono text-xs text-slate-600">
                No trace events.
              </p>
            )}
          </section>

          <section className="panel" aria-labelledby="metrics-heading">
            <h2 id="metrics-heading" className="panel-title mt-0">
              Metrics
            </h2>
            <dl className="mt-4 grid grid-cols-3 gap-3">
              {[
                ["Iterations", formatMetric(result?.metrics.iterations ?? null)],
                ["Tool Calls", formatMetric(result?.metrics.tool_calls ?? null)],
                ["Duration", formatMetric(result?.metrics.duration_ms ?? null, " ms")],
              ].map(([label, value]) => (
                <div key={label} className="rounded-md bg-slate-950 p-3">
                  <dt className="text-[11px] text-slate-500">{label}</dt>
                  <dd className="mt-2 font-mono text-sm text-slate-300">
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
