"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { usePreferences } from "@/components/preferences-provider";
import type { TranslationKey } from "@/lib/i18n";

type NavigationIconName =
  | "dashboard"
  | "web"
  | "knowledge"
  | "context"
  | "prompts"
  | "resume"
  | "github";

const navigationIconPaths: Record<NavigationIconName, string[]> = {
  dashboard: [
    "M4 4h6v6H4z",
    "M14 4h6v6h-6z",
    "M4 14h6v6H4z",
    "M14 14h6v6h-6z",
  ],
  web: [
    "M3 12h18",
    "M12 3a15 15 0 0 1 0 18",
    "M12 3a15 15 0 0 0 0 18",
    "M12 3a9 9 0 1 0 0 18",
  ],
  knowledge: [
    "M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22z",
    "M20 5.5A2.5 2.5 0 0 0 17.5 3H13v17h4.5A2.5 2.5 0 0 1 20 22z",
  ],
  context: [
    "M8 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3",
    "M16 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3",
    "M9 9h6",
    "M9 15h6",
  ],
  prompts: ["M4 5h16v11H9l-5 4z", "M8 9h8", "M8 12h5"],
  resume: [
    "M6 3h9l3 3v15H6z",
    "M14 3v4h4",
    "M9 11h6",
    "M9 15h6",
    "M9 18h4",
  ],
  github: [
    "M6 4v7a3 3 0 0 0 3 3h6",
    "M18 4v5a3 3 0 0 1-3 3H9",
    "M6 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
    "M18 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
    "M15 16a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  ],
};

const primaryNavigation = [
  { labelKey: "navigation.dashboard", href: "/", icon: "dashboard" },
  { labelKey: "navigation.context", href: "/context", icon: "context" },
  { labelKey: "navigation.prompts", href: "/prompts", icon: "prompts" },
  { labelKey: "navigation.resume", href: "/resume", icon: "resume" },
  { labelKey: "navigation.github", href: "/github", icon: "github" },
] satisfies {
  labelKey: TranslationKey;
  href: string;
  icon: NavigationIconName;
}[];

function NavigationIcon({ name }: { name: NavigationIconName }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="hidden h-4 w-4 shrink-0 md:block"
    >
      {navigationIconPaths[name].map((path) => (
        <path key={path} d={path} />
      ))}
    </svg>
  );
}

function SidebarToggleIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
      <path d={collapsed ? "m13 9 3 3-3 3" : "m16 9-3 3 3 3"} />
    </svg>
  );
}

function NavigationLink({
  href,
  labelKey,
  icon,
  collapsed,
  nested = false,
}: {
  href: string;
  labelKey: TranslationKey;
  icon: NavigationIconName;
  collapsed: boolean;
  nested?: boolean;
}) {
  const pathname = usePathname();
  const { t } = usePreferences();
  const active = pathname === href;
  const label = t(labelKey);

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      aria-label={collapsed ? label : undefined}
      title={collapsed ? label : undefined}
      className={`nav-link flex items-center gap-3 whitespace-nowrap rounded-md border px-3 py-2 text-sm ${
        nested && !collapsed ? "md:ml-3" : ""
      } ${
        collapsed ? "md:h-10 md:justify-center md:px-0" : ""
      } ${active ? "nav-link-active" : "nav-link-idle"}`}
    >
      <NavigationIcon name={icon} />
      <span className={collapsed ? "md:sr-only" : ""}>{label}</span>
    </Link>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, t, toggleSidebar } = usePreferences();
  const toggleLabel = sidebarCollapsed
    ? t("navigation.expandSidebar")
    : t("navigation.collapseSidebar");

  return (
    <aside
      data-collapsed={sidebarCollapsed}
      className={`shell-sidebar shrink-0 border-b transition-[width] duration-150 motion-reduce:transition-none md:overflow-hidden md:border-r md:border-b-0 ${
        sidebarCollapsed ? "md:w-[4.5rem]" : "md:w-60"
      }`}
    >
      <div
        className={`hidden items-center pt-5 md:flex ${
          sidebarCollapsed ? "justify-center px-2" : "justify-between px-4"
        }`}
      >
        <span
          className={`sidebar-section-label font-mono text-[10px] uppercase tracking-[0.18em] ${
            sidebarCollapsed ? "sr-only" : ""
          }`}
        >
          {t("navigation.workspaces")}
        </span>
        <button
          type="button"
          className="control-button"
          aria-label={toggleLabel}
          title={toggleLabel}
          aria-expanded={!sidebarCollapsed}
          aria-controls="workbench-navigation"
          onClick={toggleSidebar}
        >
          <SidebarToggleIcon collapsed={sidebarCollapsed} />
        </button>
      </div>
      <nav
        id="workbench-navigation"
        aria-label={t("navigation.label")}
        className={`flex gap-1 overflow-x-auto px-4 py-3 md:flex-col md:overflow-visible md:py-5 ${
          sidebarCollapsed ? "md:px-2" : "md:px-3"
        }`}
      >
        <NavigationLink
          {...primaryNavigation[0]}
          collapsed={sidebarCollapsed}
        />
        <div
          className={`sidebar-section-label hidden px-3 pt-4 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] ${
            sidebarCollapsed ? "md:hidden" : "md:block"
          }`}
        >
          {t("navigation.research")}
        </div>
        <NavigationLink
          href="/research/web"
          labelKey="navigation.webResearch"
          icon="web"
          collapsed={sidebarCollapsed}
          nested
        />
        <NavigationLink
          href="/research/knowledge"
          labelKey="navigation.knowledgeResearch"
          icon="knowledge"
          collapsed={sidebarCollapsed}
          nested
        />
        <div className="hidden pt-2 md:block" />
        {primaryNavigation.slice(1).map((item) => (
          <NavigationLink
            key={item.href}
            {...item}
            collapsed={sidebarCollapsed}
          />
        ))}
      </nav>
    </aside>
  );
}
