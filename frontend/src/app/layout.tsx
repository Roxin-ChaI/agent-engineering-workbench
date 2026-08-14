import type { Metadata } from "next";
import { HeaderControls } from "@/components/header-controls";
import { PreferencesProvider } from "@/components/preferences-provider";
import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Engineering Workbench",
  description: "A unified workbench for AI agent engineering projects.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className="h-full antialiased"
    >
      <body className="min-h-full">
        <PreferencesProvider>
          <div className="flex min-h-screen flex-col">
            <header className="shell-header flex min-h-16 shrink-0 items-center justify-between gap-3 px-5 py-3 md:px-7">
              <div className="min-w-0">
                <p className="brand-kicker">AI AGENT PLATFORM</p>
                <p className="brand-title truncate">
                  Agent Engineering Workbench
                </p>
              </div>
              <HeaderControls />
            </header>
            <div className="flex min-h-0 flex-1 flex-col md:flex-row">
              <Sidebar />
              <main className="workspace-main min-w-0 flex-1 px-5 py-8 md:px-8 lg:px-10">
                {children}
              </main>
            </div>
          </div>
        </PreferencesProvider>
      </body>
    </html>
  );
}
