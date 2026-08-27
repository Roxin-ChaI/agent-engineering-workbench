import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const sidebarSource = readFileSync(
  new URL("../src/components/sidebar.tsx", import.meta.url),
  "utf8",
);
const preferencesSource = readFileSync(
  new URL("../src/components/preferences-provider.tsx", import.meta.url),
  "utf8",
);
const layoutSource = readFileSync(
  new URL("../src/app/layout.tsx", import.meta.url),
  "utf8",
);
const promptSource = readFileSync(
  new URL("../src/components/prompt-experiment-workspace.tsx", import.meta.url),
  "utf8",
);
const i18nSource = readFileSync(
  new URL("../src/lib/i18n.ts", import.meta.url),
  "utf8",
);

test("sidebar defaults expanded and persists its desktop state safely", () => {
  assert.match(preferencesSource, /sidebarCollapsed: false/);
  assert.match(preferencesSource, /aew-sidebar-collapsed/);
  assert.match(preferencesSource, /readSidebarCollapsed\(\)/);
  assert.match(
    preferencesSource,
    /localStorage\.getItem\(SIDEBAR_STORAGE_KEY\) === "true"/,
  );
  assert.match(
    preferencesSource,
    /SIDEBAR_STORAGE_KEY,\s*String\(preferences\.sidebarCollapsed\)/,
  );
  assert.match(preferencesSource, /catch \{/);
  assert.match(preferencesSource, /toggleSidebar/);
});

test("sidebar keeps all routes, icons, active state, and its toggle", () => {
  for (const href of [
    "/",
    "/research/web",
    "/research/knowledge",
    "/context",
    "/prompts",
    "/resume",
    "/github",
  ]) {
    assert.ok(
      sidebarSource.includes(`href: "${href}"`) ||
        sidebarSource.includes(`href="${href}"`),
    );
  }
  assert.match(sidebarSource, /NavigationIcon/);
  assert.match(sidebarSource, /aria-current=\{active \? "page"/);
  assert.match(sidebarSource, /aria-label=\{toggleLabel\}/);
  assert.match(sidebarSource, /aria-controls="workbench-navigation"/);
  assert.match(sidebarSource, /id="workbench-navigation"/);
  assert.match(sidebarSource, /onClick=\{toggleSidebar\}/);
  assert.match(sidebarSource, /title=\{collapsed \? label : undefined\}/);
  assert.match(sidebarSource, /md:sr-only/);
});

test("desktop collapses to a narrow rail while mobile and main layout remain intact", () => {
  assert.match(sidebarSource, /md:w-\[4\.5rem\]/);
  assert.match(sidebarSource, /md:w-60/);
  assert.match(sidebarSource, /motion-reduce:transition-none/);
  assert.match(sidebarSource, /md:overflow-hidden/);
  assert.match(layoutSource, /md:flex-row/);
  assert.match(layoutSource, /workspace-main min-w-0 flex-1/);
});

test("sidebar controls are bilingual and prompt workspace stays untouched", () => {
  for (const key of [
    "navigation.workspaces",
    "navigation.collapseSidebar",
    "navigation.expandSidebar",
  ]) {
    assert.equal(i18nSource.split(`"${key}"`).length - 1, 2);
  }
  assert.match(promptSource, /prompt-placeholder/);
  assert.match(promptSource, /await runPromptExperiment\(request\)/);
});
