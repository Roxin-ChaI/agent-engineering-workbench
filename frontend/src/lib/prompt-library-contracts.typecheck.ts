import type {
  PromptLibraryCreateRequest,
  PromptLibraryItem,
  PromptLibraryUpdateRequest,
} from "@/lib/contracts";

type Assert<T extends true> = T;
type IsNever<T> = [T] extends [never] ? true : false;

export const promptLibraryItemFixture = {
  id: 1,
  title: "Research Assistant",
  content: "Use sources carefully.",
  wiki_rules: ["First rule", "Second rule"],
  tags: ["research", "grounded"],
} satisfies PromptLibraryItem;

export const promptLibraryEmptyRulesFixture = {
  ...promptLibraryItemFixture,
  wiki_rules: [],
} satisfies PromptLibraryItem;

export const promptLibraryCreateFixture = {
  title: "Research Assistant",
  content: "Use sources carefully.",
  wiki_rules: ["First rule", "Second rule"],
  tags: ["research", "grounded"],
} satisfies PromptLibraryCreateRequest;

export const promptLibraryOmittedUpdateFixture = {
  title: "Updated",
} satisfies PromptLibraryUpdateRequest;

export const promptLibraryEmptyRulesUpdateFixture = {
  wiki_rules: [],
} satisfies PromptLibraryUpdateRequest;

export const promptLibraryNonEmptyUpdateFixture = {
  wiki_rules: ["rule-a", "rule-b"],
} satisfies PromptLibraryUpdateRequest;

type ForbiddenPromptLibraryKeys =
  | "task"
  | "criteria"
  | "variants"
  | "max_steps"
  | "seed"
  | "evaluation"
  | "result"
  | "history"
  | "api_key"
  | "base_url";

type PromptLibraryKeys =
  | keyof PromptLibraryItem
  | keyof PromptLibraryCreateRequest
  | keyof PromptLibraryUpdateRequest;

export type PromptLibraryContractsStayInScope = Assert<
  IsNever<Extract<PromptLibraryKeys, ForbiddenPromptLibraryKeys>>
>;

export type PromptLibraryIdIsNumeric = Assert<
  PromptLibraryItem["id"] extends number ? true : false
>;
