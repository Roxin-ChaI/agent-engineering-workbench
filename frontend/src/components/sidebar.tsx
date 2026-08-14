"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const primaryNavigation = [
  { label: "Dashboard", href: "/" },
  { label: "Context", href: "/context" },
  { label: "Prompts", href: "/prompts" },
  { label: "Resume", href: "/resume" },
  { label: "GitHub", href: "/github" },
];

function NavigationLink({
  href,
  label,
  nested = false,
}: {
  href: string;
  label: string;
  nested?: boolean;
}) {
  const pathname = usePathname();
  const active = pathname === href;

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`block whitespace-nowrap rounded-md border px-3 py-2 text-sm transition-colors ${
        nested ? "md:ml-3" : ""
      } ${
        active
          ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-200"
          : "border-transparent text-slate-400 hover:bg-slate-900 hover:text-slate-100"
      }`}
    >
      {label}
    </Link>
  );
}

export function Sidebar() {
  return (
    <aside className="shrink-0 border-b border-slate-800 bg-slate-950 md:w-60 md:border-r md:border-b-0">
      <nav
        aria-label="Workbench navigation"
        className="flex gap-1 overflow-x-auto px-4 py-3 md:flex-col md:overflow-visible md:px-3 md:py-6"
      >
        <NavigationLink {...primaryNavigation[0]} />
        <div className="hidden px-3 pt-4 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-600 md:block">
          Research
        </div>
        <NavigationLink href="/research/web" label="Web Research" nested />
        <div className="hidden pt-2 md:block" />
        {primaryNavigation.slice(1).map((item) => (
          <NavigationLink key={item.href} {...item} />
        ))}
      </nav>
    </aside>
  );
}
