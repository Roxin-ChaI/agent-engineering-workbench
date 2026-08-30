import type { PromptLibraryItem } from "@/lib/contracts";

export function splitPromptLibraryLines(value: string): string[] {
  return value
    .split(/\r?\n/u)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function parsePromptLibraryTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

export function promptLibraryRulesToText(rules: string[]): string {
  return rules.join("\n");
}

export function upsertPromptLibraryItem(
  items: PromptLibraryItem[],
  item: PromptLibraryItem,
): PromptLibraryItem[] {
  const index = items.findIndex((candidate) => candidate.id === item.id);
  if (index === -1) {
    return [...items, item];
  }

  return items.map((candidate) => (candidate.id === item.id ? item : candidate));
}

export function removePromptLibraryItem(
  items: PromptLibraryItem[],
  promptId: number,
): PromptLibraryItem[] {
  return items.filter((item) => item.id !== promptId);
}

export function selectedPromptAfterDelete(
  selectedPromptId: number | null,
  deletedPromptId: number,
): number | null {
  return selectedPromptId === deletedPromptId ? null : selectedPromptId;
}
