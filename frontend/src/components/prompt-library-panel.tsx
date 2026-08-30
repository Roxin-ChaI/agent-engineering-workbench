"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { usePreferences } from "@/components/preferences-provider";
import {
  createPromptLibraryItem,
  deletePromptLibraryItem,
  listPromptLibraryItems,
  searchPromptLibraryItems,
  updatePromptLibraryItem,
} from "@/lib/api";
import type { PromptLibraryItem } from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";
import {
  parsePromptLibraryTags,
  removePromptLibraryItem,
  selectedPromptAfterDelete,
  splitPromptLibraryLines,
  upsertPromptLibraryItem,
} from "@/lib/prompt-library-workspace-state";

type Feedback = {
  kind: "error" | "success";
  key: TranslationKey;
};

type Mutation = "save" | "update" | `delete:${number}`;

function errorStatus(error: unknown): string | null {
  if (!(error instanceof Error)) {
    return null;
  }
  return error.message.match(/status (\d{3})/u)?.[1] ?? null;
}

function libraryErrorKey(error: unknown): TranslationKey {
  const status = errorStatus(error);
  if (status === "422") {
    return "prompt.libraryInvalid";
  }
  if (status === "404") {
    return "prompt.libraryNotFound";
  }
  if (status === "502") {
    return "prompt.libraryUnavailable";
  }
  if (status === "500") {
    return "prompt.libraryInternalError";
  }
  return "prompt.libraryNetworkError";
}

export function PromptLibraryPanel({
  systemPrompt,
  wikiRules,
  onLoadPrompt,
}: {
  systemPrompt: string;
  wikiRules: string;
  onLoadPrompt: (item: PromptLibraryItem) => void;
}) {
  const { t } = usePreferences();
  const [items, setItems] = useState<PromptLibraryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState(false);
  const [title, setTitle] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [mutation, setMutation] = useState<Mutation | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const initialLoadStarted = useRef(false);

  useEffect(() => {
    if (initialLoadStarted.current) {
      return;
    }
    initialLoadStarted.current = true;
    void listPromptLibraryItems()
      .then((loadedItems) => {
        setItems(loadedItems);
      })
      .catch((requestError: unknown) => {
        setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
      })
      .finally(() => {
        setListLoading(false);
      });
  }, []);

  async function loadAllPrompts() {
    setListLoading(true);
    setFeedback(null);
    try {
      setItems(await listPromptLibraryItems());
      setActiveSearch(false);
    } catch (requestError) {
      setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
    } finally {
      setListLoading(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    if (!query || listLoading) {
      return;
    }

    setListLoading(true);
    setFeedback(null);
    try {
      setItems(await searchPromptLibraryItems(query));
      setActiveSearch(true);
    } catch (requestError) {
      setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
    } finally {
      setListLoading(false);
    }
  }

  function handleLoad(item: PromptLibraryItem) {
    onLoadPrompt(item);
    setSelectedPromptId(item.id);
    setTitle(item.title);
    setTagsInput(item.tags.join(", "));
    setFeedback({ kind: "success", key: "prompt.libraryLoaded" });
  }

  function validatedEditorInput(): {
    title: string;
    tags: string[];
  } | null {
    const normalizedTitle = title.trim();
    if (!normalizedTitle) {
      setFeedback({ kind: "error", key: "prompt.libraryTitleRequired" });
      return null;
    }
    if (!systemPrompt.trim()) {
      setFeedback({ kind: "error", key: "prompt.libraryContentRequired" });
      return null;
    }
    return {
      title: normalizedTitle,
      tags: parsePromptLibraryTags(tagsInput),
    };
  }

  async function handleSave() {
    if (mutation !== null) {
      return;
    }
    const editorInput = validatedEditorInput();
    if (editorInput === null) {
      return;
    }

    setMutation("save");
    setFeedback(null);
    try {
      const created = await createPromptLibraryItem({
        title: editorInput.title,
        content: systemPrompt,
        wiki_rules: splitPromptLibraryLines(wikiRules),
        tags: editorInput.tags,
      });
      setItems((currentItems) => upsertPromptLibraryItem(currentItems, created));
      setSelectedPromptId(created.id);
      setTitle(created.title);
      setTagsInput(created.tags.join(", "));
      setFeedback({ kind: "success", key: "prompt.librarySaved" });
    } catch (requestError) {
      setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
    } finally {
      setMutation(null);
    }
  }

  async function handleUpdate() {
    if (mutation !== null || selectedPromptId === null) {
      return;
    }
    const editorInput = validatedEditorInput();
    if (editorInput === null) {
      return;
    }

    setMutation("update");
    setFeedback(null);
    try {
      const updated = await updatePromptLibraryItem(selectedPromptId, {
        title: editorInput.title,
        content: systemPrompt,
        wiki_rules: splitPromptLibraryLines(wikiRules),
        tags: editorInput.tags,
      });
      setItems((currentItems) => upsertPromptLibraryItem(currentItems, updated));
      setFeedback({ kind: "success", key: "prompt.libraryUpdated" });
    } catch (requestError) {
      setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
    } finally {
      setMutation(null);
    }
  }

  async function handleDelete(item: PromptLibraryItem) {
    if (mutation !== null || !window.confirm(t("prompt.libraryDeleteConfirm"))) {
      return;
    }

    setMutation(`delete:${item.id}`);
    setFeedback(null);
    try {
      await deletePromptLibraryItem(item.id);
      setItems((currentItems) =>
        removePromptLibraryItem(currentItems, item.id),
      );
      setSelectedPromptId((currentId) =>
        selectedPromptAfterDelete(currentId, item.id),
      );
      setFeedback({ kind: "success", key: "prompt.libraryDeleted" });
    } catch (requestError) {
      setFeedback({ kind: "error", key: libraryErrorKey(requestError) });
    } finally {
      setMutation(null);
    }
  }

  return (
    <section className="panel mt-8 min-w-0" aria-labelledby="library-heading">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 id="library-heading" className="panel-title mt-0">
            {t("prompt.libraryTitle")}
          </h2>
          <p className="panel-copy max-w-2xl">{t("prompt.libraryDescription")}</p>
        </div>
        <p className="text-muted text-xs" aria-live="polite">
          {selectedPromptId !== null
            ? `${t("prompt.librarySelected")}: ${title}`
            : t("prompt.libraryNoSelection")}
        </p>
      </div>

      <div className="mt-5 grid min-w-0 gap-5 xl:grid-cols-[minmax(17rem,0.7fr)_minmax(0,1.3fr)]">
        <div className="min-w-0 space-y-4">
          <div>
            <label
              htmlFor="prompt-library-title"
              className="text-primary block text-sm font-medium"
            >
              {t("prompt.libraryPromptTitle")}
            </label>
            <input
              id="prompt-library-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={t("prompt.libraryTitlePlaceholder")}
              className="prompt-placeholder workbench-input mt-2 w-full rounded-md border px-3 py-2 text-sm outline-none"
            />
          </div>
          <div>
            <label
              htmlFor="prompt-library-tags"
              className="text-primary block text-sm font-medium"
            >
              {t("prompt.libraryTags")}
            </label>
            <input
              id="prompt-library-tags"
              value={tagsInput}
              onChange={(event) => setTagsInput(event.target.value)}
              placeholder={t("prompt.libraryTagsPlaceholder")}
              className="prompt-placeholder workbench-input mt-2 w-full rounded-md border px-3 py-2 text-sm outline-none"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={mutation !== null}
              onClick={() => void handleSave()}
              className="primary-action rounded-md border px-3 py-2 text-sm font-medium"
            >
              {mutation === "save"
                ? t("prompt.librarySaving")
                : t("prompt.librarySave")}
            </button>
            <button
              type="button"
              disabled={selectedPromptId === null || mutation !== null}
              onClick={() => void handleUpdate()}
              className="control-button rounded-md border px-3 py-2 text-sm"
            >
              {mutation === "update"
                ? t("prompt.libraryUpdating")
                : t("prompt.libraryUpdate")}
            </button>
          </div>
          <p className="text-muted text-xs leading-5">
            {t("prompt.librarySaveHint")}
          </p>
          {feedback ? (
            <p
              className={feedback.kind === "error" ? "text-error text-sm" : "text-accent text-sm"}
              role={feedback.kind === "error" ? "alert" : "status"}
            >
              {t(feedback.key)}
            </p>
          ) : null}
        </div>

        <div className="min-w-0">
          <form
            className="flex min-w-0 flex-col gap-2 sm:flex-row"
            onSubmit={handleSearch}
          >
            <label htmlFor="prompt-library-search" className="sr-only">
              {t("prompt.librarySearch")}
            </label>
            <input
              id="prompt-library-search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t("prompt.librarySearchPlaceholder")}
              className="prompt-placeholder workbench-input min-w-0 flex-1 rounded-md border px-3 py-2 text-sm outline-none"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={listLoading || !searchQuery.trim()}
                className="primary-action flex-1 rounded-md border px-3 py-2 text-sm font-medium sm:flex-none"
              >
                {t("prompt.librarySearchAction")}
              </button>
              <button
                type="button"
                disabled={listLoading || !activeSearch}
                onClick={() => {
                  setSearchQuery("");
                  void loadAllPrompts();
                }}
                className="control-button flex-1 rounded-md border px-3 py-2 text-sm sm:flex-none"
              >
                {t("prompt.libraryClearSearch")}
              </button>
            </div>
          </form>

          <div className="mt-4" aria-busy={listLoading}>
            {listLoading ? (
              <p className="text-muted text-sm">{t("prompt.libraryLoading")}</p>
            ) : items.length > 0 ? (
              <ul className="grid min-w-0 gap-3 md:grid-cols-2">
                {items.map((item) => (
                  <li
                    key={item.id}
                    className="metric-card min-w-0 rounded-md p-4"
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="text-primary truncate text-sm font-semibold">
                          {item.title}
                        </h3>
                        <p className="text-muted mt-2 line-clamp-2 break-words text-xs leading-5">
                          {item.content}
                        </p>
                      </div>
                      {selectedPromptId === item.id ? (
                        <span className="status-completed rounded-md border px-2 py-1 font-mono text-[9px] uppercase tracking-wider">
                          {t("prompt.librarySelectedBadge")}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {item.tags.map((tag, index) => (
                        <span
                          key={`${tag}-${index}`}
                          className="text-accent rounded border border-[var(--accent-border)] px-2 py-0.5 text-[10px]"
                        >
                          {tag}
                        </span>
                      ))}
                      <span className="text-muted px-1 py-0.5 text-[10px]">
                        {t("prompt.libraryRules")}: {item.wiki_rules.length}
                      </span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleLoad(item)}
                        className="primary-action rounded-md border px-2.5 py-1.5 text-xs font-medium"
                      >
                        {t("prompt.libraryLoad")}
                      </button>
                      <button
                        type="button"
                        disabled={mutation !== null}
                        onClick={() => void handleDelete(item)}
                        className="control-button rounded-md border px-2.5 py-1.5 text-xs"
                      >
                        {mutation === `delete:${item.id}`
                          ? t("prompt.libraryDeleting")
                          : t("prompt.libraryDelete")}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : feedback?.kind === "error" ? null : (
              <p className="text-muted text-sm">
                {activeSearch
                  ? t("prompt.librarySearchEmpty")
                  : t("prompt.libraryEmpty")}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
