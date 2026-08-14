export function ComingSoon({ title }: { title: string }) {
  return (
    <section className="mx-auto max-w-6xl">
      <p className="section-label">Workbench / Planned</p>
      <h1 className="page-title">{title}</h1>
      <div className="panel mt-8 max-w-2xl border-dashed">
        <p className="font-mono text-sm text-slate-300">Coming Soon</p>
        <p className="panel-copy">
          This workspace is reserved for a future Workbench integration.
        </p>
      </div>
    </section>
  );
}
