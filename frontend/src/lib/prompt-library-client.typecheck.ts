import {
  createPromptLibraryItem,
  deletePromptLibraryItem,
  getPromptLibraryItem,
  listPromptLibraryItems,
  searchPromptLibraryItems,
  updatePromptLibraryItem,
} from "@/lib/api";
import type {
  PromptLibraryCreateRequest,
  PromptLibraryItem,
  PromptLibraryUpdateRequest,
} from "@/lib/contracts";

type Assert<T extends true> = T;
type Equal<Left, Right> =
  (<Value>() => Value extends Left ? 1 : 2) extends <Value>() =>
    Value extends Right ? 1 : 2
    ? true
    : false;

export type CreatePromptLibraryClientSignatureMatches = Assert<
  Equal<
    typeof createPromptLibraryItem,
    (request: PromptLibraryCreateRequest) => Promise<PromptLibraryItem>
  >
>;

export type ListPromptLibraryClientSignatureMatches = Assert<
  Equal<typeof listPromptLibraryItems, () => Promise<PromptLibraryItem[]>>
>;

export type GetPromptLibraryClientSignatureMatches = Assert<
  Equal<typeof getPromptLibraryItem, (id: number) => Promise<PromptLibraryItem>>
>;

export type SearchPromptLibraryClientSignatureMatches = Assert<
  Equal<
    typeof searchPromptLibraryItems,
    (q: string) => Promise<PromptLibraryItem[]>
  >
>;

export type UpdatePromptLibraryClientSignatureMatches = Assert<
  Equal<
    typeof updatePromptLibraryItem,
    (
      id: number,
      request: PromptLibraryUpdateRequest,
    ) => Promise<PromptLibraryItem>
  >
>;

export type DeletePromptLibraryClientSignatureMatches = Assert<
  Equal<typeof deletePromptLibraryItem, (id: number) => Promise<void>>
>;
