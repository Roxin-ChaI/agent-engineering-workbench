import type { Metadata } from "next";
import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Engineering Workbench",
  description: "A unified workbench for AI agent engineering projects.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-950 text-slate-100">
        <div className="flex min-h-screen flex-col">
          <header className="flex h-16 shrink-0 items-center border-b border-slate-800 bg-slate-950 px-5 md:px-7">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-cyan-400">
                AI Agent Platform
              </p>
              <p className="mt-1 text-sm font-semibold tracking-wide text-slate-100 sm:text-base">
                Agent Engineering Workbench
              </p>
            </div>
          </header>
          <div className="flex min-h-0 flex-1 flex-col md:flex-row">
            <Sidebar />
            <main className="min-w-0 flex-1 bg-slate-950 px-5 py-8 md:px-8 lg:px-10">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
