import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const librarySource = readFileSync(
  new URL("../src/components/prompt-library-panel.tsx", import.meta.url),
  "utf8",
);
const experimentSource = readFileSync(
  new URL("../src/components/prompt-experiment-workspace.tsx", import.meta.url),
  "utf8",
);
const i18nSource = readFileSync(
  new URL("../src/lib/i18n.ts", import.meta.url),
  "utf8",
);
const frontendSource = `${librarySource}\n${experimentSource}`;

test("library initializes through Workbench and has loading, empty, and error states", () => {
  assert.match(librarySource, /useEffect\(\(\) => \{/);
  assert.match(librarySource, /listPromptLibraryItems\(\)/);
  assert.match(librarySource, /prompt\.libraryLoading/);
  assert.match(librarySource, /prompt\.libraryEmpty/);
  assert.match(librarySource, /libraryErrorKey\(requestError\)/);
});

test("search submits to Workbench and clear restores the backend list", () => {
  assert.match(librarySource, /searchPromptLibraryItems\(query\)/);
  assert.match(librarySource, /setActiveSearch\(true\)/);
  assert.match(librarySource, /setSearchQuery\(""\)/);
  assert.match(librarySource, /void loadAllPrompts\(\)/);
  assert.match(librarySource, /prompt\.librarySearchEmpty/);
});

test("save stores only title, current prompt bundle, and ordered tags", () => {
  const saveBlock = librarySource.match(
    /createPromptLibraryItem\(\{([\s\S]*?)\}\);/u,
  );
  assert.ok(saveBlock);
  assert.match(saveBlock[1], /title: editorInput\.title/);
  assert.match(saveBlock[1], /content: systemPrompt/);
  assert.match(saveBlock[1], /wiki_rules: splitPromptLibraryLines\(wikiRules\)/);
  assert.match(saveBlock[1], /tags: editorInput\.tags/);
  for (const excluded of ["task", "criteria", "variant", "maxSteps", "seed", "result"]) {
    assert.doesNotMatch(saveBlock[1], new RegExp(excluded, "u"));
  }
});

test("load changes only system prompt and ordered wiki rules", () => {
  const loadCallback = experimentSource.match(
    /onLoadPrompt=\{\(item: PromptLibraryItem\) => \{([\s\S]*?)\}\}/u,
  );
  assert.ok(loadCallback);
  assert.match(loadCallback[1], /setSystemPrompt\(item\.content\)/);
  assert.match(
    loadCallback[1],
    /setWikiRules\(promptLibraryRulesToText\(item\.wiki_rules\)\)/,
  );
  for (const forbiddenSetter of [
    "setTaskId",
    "setInstruction",
    "setVariant",
    "setMaxSteps",
    "setSeed",
    "setResult",
  ]) {
    assert.doesNotMatch(loadCallback[1], new RegExp(forbiddenSetter, "u"));
  }
});

test("update always sends the complete selected bundle including empty rules", () => {
  const updateBlock = librarySource.match(
    /updatePromptLibraryItem\(selectedPromptId, \{([\s\S]*?)\}\);/u,
  );
  assert.ok(updateBlock);
  assert.match(updateBlock[1], /content: systemPrompt/);
  assert.match(updateBlock[1], /wiki_rules: splitPromptLibraryLines\(wikiRules\)/);
  assert.match(updateBlock[1], /title: editorInput\.title/);
  assert.match(updateBlock[1], /tags: editorInput\.tags/);
});

test("confirmed delete removes state and clears matching selection only", () => {
  assert.match(librarySource, /window\.confirm\(t\("prompt\.libraryDeleteConfirm"\)\)/);
  assert.match(librarySource, /await deletePromptLibraryItem\(item\.id\)/);
  assert.match(librarySource, /removePromptLibraryItem\(currentItems, item\.id\)/);
  assert.match(librarySource, /selectedPromptAfterDelete\(currentId, item\.id\)/);
});

test("library and experiment loading states remain isolated", () => {
  assert.match(librarySource, /aria-busy=\{listLoading\}/);
  assert.match(experimentSource, /aria-busy=\{loading\}/);
  assert.doesNotMatch(experimentSource, /disabled=\{listLoading\}/);
  assert.doesNotMatch(librarySource, /setLoading\(/);
});

test("library layout is compact, responsive, themed, and keeps placeholders", () => {
  assert.match(librarySource, /xl:grid-cols-/);
  assert.match(librarySource, /md:grid-cols-2/);
  assert.match(librarySource, /flex-wrap/);
  assert.match(librarySource, /line-clamp-2/);
  assert.match(librarySource, /workbench-input/);
  assert.match(librarySource, /metric-card/);
  assert.match(librarySource, /prompt-placeholder/);
  assert.match(experimentSource, /prompt-placeholder/);
});

test("all visible library text has matching English and Chinese keys", () => {
  const visibleKeys = [...librarySource.matchAll(/t\("(prompt\.library[^"]+)"\)/gu)].map(
    ([, key]) => key,
  );
  assert.ok(visibleKeys.length > 20);
  for (const key of new Set(visibleKeys)) {
    assert.equal(i18nSource.split(`"${key}"`).length - 1, 2, key);
  }
});

test("browser source references only Workbench Prompt Library APIs", () => {
  for (const forbidden of [
    "PROMPT_VAULT_BASE_URL",
    "PromptVaultHttpClient",
    "prompt-vault",
    "127.0.0.1:8001",
  ]) {
    assert.doesNotMatch(frontendSource, new RegExp(forbidden, "u"));
  }
  assert.match(librarySource, /@\/lib\/api/);
});
