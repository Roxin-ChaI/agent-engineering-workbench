"use client";

import { usePreferences } from "@/components/preferences-provider";

export default function DashboardPage() {
  const { t } = usePreferences();

  return (
    <section className="mx-auto max-w-6xl">
      <p className="section-label">{t("dashboard.section")}</p>
      <h1 className="page-title">{t("dashboard.title")}</h1>
      <p className="page-description">{t("dashboard.description")}</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <article className="panel">
          <p className="panel-kicker">{t("dashboard.availableWorkspace")}</p>
          <h2 className="panel-title">{t("dashboard.webResearch")}</h2>
          <p className="panel-copy">{t("dashboard.webResearchDescription")}</p>
        </article>
        <article className="panel">
          <p className="panel-kicker">{t("dashboard.workbenchMode")}</p>
          <h2 className="panel-title">{t("dashboard.localDevelopment")}</h2>
          <p className="panel-copy">
            {t("dashboard.localDevelopmentDescription")}
          </p>
        </article>
        <article className="panel sm:col-span-2 xl:col-span-1">
          <p className="panel-kicker">{t("dashboard.projectScope")}</p>
          <h2 className="panel-title">{t("dashboard.version")}</h2>
          <p className="panel-copy">{t("dashboard.scopeDescription")}</p>
        </article>
      </div>
    </section>
  );
}
