export default function WebResearchPage() {
  return (
    <section className="mx-auto max-w-6xl">
      <p className="section-label">Research / Workspace</p>
      <h1 className="page-title">Web Research</h1>
      <p className="page-description">
        Prepare a research question and inspect the final answer, agent
        activity, and run metrics in one workspace.
      </p>

      <div className="mt-8 grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.8fr)]">
        <div className="space-y-4">
          <section className="panel" aria-labelledby="question-heading">
            <div className="flex items-center justify-between gap-4">
              <h2 id="question-heading" className="panel-title mt-0">
                Question
              </h2>
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">
                Input
              </span>
            </div>
            <label htmlFor="research-question" className="sr-only">
              Research question
            </label>
            <textarea
              id="research-question"
              rows={4}
              placeholder="Enter a research question..."
              className="mt-4 w-full resize-none rounded-md border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500"
            />
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                disabled
                className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-300 opacity-60"
              >
                Run research
              </button>
            </div>
          </section>

          <section className="panel min-h-52" aria-labelledby="answer-heading">
            <h2 id="answer-heading" className="panel-title mt-0">
              Answer
            </h2>
            <p className="mt-8 text-sm text-slate-600">
              The research answer will appear here after a run.
            </p>
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
            <div className="mt-5 border-l border-slate-800 pl-4">
              <p className="font-mono text-xs text-slate-600">
                No activity recorded
              </p>
            </div>
          </section>

          <section className="panel" aria-labelledby="metrics-heading">
            <h2 id="metrics-heading" className="panel-title mt-0">
              Metrics
            </h2>
            <dl className="mt-4 grid grid-cols-3 gap-3">
              {[
                ["Iterations", "—"],
                ["Tool calls", "—"],
                ["Duration", "—"],
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
