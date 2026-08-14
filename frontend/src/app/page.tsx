export default function DashboardPage() {
  return (
    <section className="mx-auto max-w-6xl">
      <p className="section-label">Workbench / Overview</p>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-description">
        A single surface for running, inspecting, and comparing agent
        engineering projects.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <article className="panel">
          <p className="panel-kicker">Available workspace</p>
          <h2 className="panel-title">Web Research</h2>
          <p className="panel-copy">
            The first integration surface for research runs, activity, and
            metrics.
          </p>
        </article>
        <article className="panel">
          <p className="panel-kicker">Workbench mode</p>
          <h2 className="panel-title">Local development</h2>
          <p className="panel-copy">
            This shell is ready for backend integration in a later step.
          </p>
        </article>
        <article className="panel sm:col-span-2 xl:col-span-1">
          <p className="panel-kicker">Project scope</p>
          <h2 className="panel-title">v0.1.0</h2>
          <p className="panel-copy">
            Navigation and workspace foundations are in place without live
            requests.
          </p>
        </article>
      </div>
    </section>
  );
}
