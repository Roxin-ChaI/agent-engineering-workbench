import assert from "node:assert/strict";
import test from "node:test";

import {
  parsePromptLibraryTags,
  promptLibraryRulesToText,
  removePromptLibraryItem,
  selectedPromptAfterDelete,
  splitPromptLibraryLines,
  upsertPromptLibraryItem,
} from "../src/lib/prompt-library-workspace-state.ts";

const firstItem = {
  id: 1,
  title: "First",
  content: "System A",
  wiki_rules: ["Rule A", "Rule B"],
  tags: ["research", "agent"],
};

const secondItem = {
  ...firstItem,
  id: 2,
  title: "Second",
};

test("tags split on commas, trim blanks, and preserve order and duplicates", () => {
  assert.deepEqual(
    parsePromptLibraryTags(" research, agent, , research "),
    ["research", "agent", "research"],
  );
});

test("wiki rules preserve line order and support explicit empty values", () => {
  assert.deepEqual(splitPromptLibraryLines(" Rule A\n\n Rule B "), [
    "Rule A",
    "Rule B",
  ]);
  assert.deepEqual(splitPromptLibraryLines("  \n"), []);
  assert.equal(promptLibraryRulesToText(["Rule 1", "Rule 2"]), "Rule 1\nRule 2");
  assert.equal(promptLibraryRulesToText([]), "");
});

test("create results append without reordering current library records", () => {
  assert.deepEqual(upsertPromptLibraryItem([firstItem], secondItem), [
    firstItem,
    secondItem,
  ]);
});

test("update results replace in place without reordering records", () => {
  const updated = { ...firstItem, title: "Updated" };

  assert.deepEqual(
    upsertPromptLibraryItem([firstItem, secondItem], updated),
    [updated, secondItem],
  );
});

test("delete removes only its item and clears only matching selection", () => {
  assert.deepEqual(removePromptLibraryItem([firstItem, secondItem], 1), [
    secondItem,
  ]);
  assert.equal(selectedPromptAfterDelete(1, 1), null);
  assert.equal(selectedPromptAfterDelete(2, 1), 2);
  assert.equal(selectedPromptAfterDelete(null, 1), null);
});
