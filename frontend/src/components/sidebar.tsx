"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { usePreferences } from "@/components/preferences-provider";
import type { TranslationKey } from "@/lib/i18n";

const primaryNavigation = [
  { labelKey: "navigation.dashboard", href: "/" },
  { labelKey: "navigation.context", href: "/context" },
  { labelKey: "navigation.prompts", href: "/prompts" },
  { labelKey: "navigation.resume", href: "/resume" },
  { labelKey: "navigation.github", href: "/github" },
] satisfies { labelKey: TranslationKey; href: string }[];

function NavigationLink({
  href,
  labelKey,
  nested = false,
}: {
  href: string;
  labelKey: TranslationKey;
  nested?: boolean;
}) {
  const pathname = usePathname();
  const { t } = usePreferences();
  const active = pathname === href;

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`nav-link block whitespace-nowrap rounded-md border px-3 py-2 text-sm ${
        nested ? "md:ml-3" : ""
      } ${active ? "nav-link-active" : "nav-link-idle"}`}
    >
      {t(labelKey)}
    </Link>
  );
}

export function Sidebar() {
  const { t } = usePreferences();

  return (
    <aside className="shell-sidebar shrink-0 border-b md:w-60 md:border-r md:border-b-0">
      <nav
        aria-label={t("navigation.label")}
        className="flex gap-1 overflow-x-auto px-4 py-3 md:flex-col md:overflow-visible md:px-3 md:py-6"
      >
        <NavigationLink {...primaryNavigation[0]} />
        <div className="sidebar-section-label hidden px-3 pt-4 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] md:block">
          {t("navigation.research")}
        </div>
        <NavigationLink
          href="/research/web"
          labelKey="navigation.webResearch"
          nested
        />
        <div className="hidden pt-2 md:block" />
        {primaryNavigation.slice(1).map((item) => (
          <NavigationLink key={item.href} {...item} />
        ))}
      </nav>
    </aside>
  );
}
