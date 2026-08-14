"use client";

import { usePreferences } from "@/components/preferences-provider";
import type { TranslationKey } from "@/lib/i18n";

export function ComingSoon({ titleKey }: { titleKey: TranslationKey }) {
  const { t } = usePreferences();

  return (
    <section className="mx-auto max-w-6xl">
      <p className="section-label">{t("comingSoon.section")}</p>
      <h1 className="page-title">{t(titleKey)}</h1>
      <div className="panel mt-8 max-w-2xl border-dashed">
        <p className="text-secondary font-mono text-sm">
          {t("comingSoon.title")}
        </p>
        <p className="panel-copy">{t("comingSoon.description")}</p>
      </div>
    </section>
  );
}
