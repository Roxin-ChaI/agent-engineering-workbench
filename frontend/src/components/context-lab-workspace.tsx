"use client";

import { type FormEvent, useRef, useState } from "react";

import { usePreferences } from "@/components/preferences-provider";
import { compressContext } from "@/lib/api";
import type {
  ContextCompressionResult,
  ContextCompressionStrategy,
  ContextMessage,
} from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";

const exampleMessages = JSON.stringify(
  [
    {
      role: "system",
      content: "You are a helpful assistant.",
    },
    {
      role: "user",
      content: "Explain why context windows need careful management.",
    },
    {
      role: "assistant",
      content:
        "Context windows are finite, so applications must preserve the most useful information.",
    },
    {
      role: "user",
      content: "How can compression help?",
    },
    {
      role: "assistant",
      content:
        "Compression reduces older context while retaining messages needed for the current task.",
    },
  ],
  null,
  2,
);

const strategyLabelKeys: Record<
  ContextCompressionStrategy,
  TranslationKey
> = {
  no_compression: "context.strategyNoCompression",
  truncation: "context.strategyTruncation",
  windowed: "context.strategyWindowed",
};

type ContextError =
  | "invalidJson"
  | "invalidRoot"
  | "invalidBudget"
  | "request";

const errorLabelKeys: Record<ContextError, TranslationKey> = {
  invalidJson: "context.invalidJson",
  invalidRoot: "context.invalidRoot",
  invalidBudget: "context.invalidBudget",
  request: "context.requestError",
};

function formatRatio(value: number): string {
  return `${Number((value * 100).toFixed(1))}%`;
}

function formatDuration(value: number): string {
  return `${Number(value.toFixed(1))} ms`;
}

function MessageList({
  messages,
  emptyLabel,
}: {
  messages: ContextMessage[];
  emptyLabel: string;
}) {
  if (messages.length === 0) {
    return <p className="text-muted mt-5 text-sm">{emptyLabel}</p>;
  }

  return (
    <ol className="mt-5 space-y-3">
      {messages.map((message, index) => (
        <li
          key={`${index}-${message.role}`}
          className="metric-card rounded-md p-4"
        >
          <p className="text-accent font-mono text-[11px] uppercase tracking-wider">
            {message.role}
          </p>
          <p className="text-secondary mt-2 whitespace-pre-wrap break-words text-sm leading-6">
            {message.content ?? "—"}
          </p>
        </li>
      ))}
    </ol>
  );
}

export function ContextLabWorkspace() {
  const { t } = usePreferences();
  const [messagesJson, setMessagesJson] = useState(exampleMessages);
  const [strategy, setStrategy] =
    useState<ContextCompressionStrategy>("truncation");
  const [targetBudget, setTargetBudget] = useState("256");
  const [maxBudget, setMaxBudget] = useState("512");
  const [result, setResult] = useState<ContextCompressionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ContextError | null>(null);
  const inFlight = useRef(false);

  const numericTargetBudget = Number(targetBudget);
  const numericMaxBudget = Number(maxBudget);
  const budgetsArePositive =
    Number.isFinite(numericTargetBudget) &&
    numericTargetBudget > 0 &&
    Number.isFinite(numericMaxBudget) &&
    numericMaxBudget > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || inFlight.current) {
      return;
    }

    setError(null);
    setResult(null);

    let parsedMessages: unknown;
    try {
      parsedMessages = JSON.parse(messagesJson);
    } catch {
      setError("invalidJson");
      return;
    }

    if (!Array.isArray(parsedMessages)) {
      setError("invalidRoot");
      return;
    }
    if (!budgetsArePositive) {
      setError("invalidBudget");
      return;
    }

    inFlight.current = true;
    setLoading(true);
    try {
      const compressionResult = await compressContext({
        messages: parsedMessages as ContextMessage[],
        target_token_budget: numericTargetBudget,
        max_token_budget: numericMaxBudget,
        strategy,
      });
      setResult(compressionResult);
    } catch {
      setError("request");
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }

  const metrics = result
    ? [
        [
          t("context.estimatedOriginalTokens"),
          String(result.original_token_estimate),
        ],
        [
          t("context.estimatedCompressedTokens"),
          String(result.compressed_token_estimate),
        ],
        [t("context.tokensSaved"), String(result.tokens_saved_estimate)],
        [t("context.compressionRatio"), formatRatio(result.compression_ratio)],
        [t("context.strategy"), t(strategyLabelKeys[result.strategy])],
        [t("context.duration"), formatDuration(result.duration_ms)],
      ]
    : [];

  return (
    <section className="mx-auto max-w-7xl">
      <p className="section-label">{t("context.section")}</p>
      <h1 className="page-title">{t("context.title")}</h1>
      <p className="page-description">{t("context.description")}</p>

      <div className="mt-8 grid gap-4 xl:grid-cols-[minmax(22rem,0.85fr)_minmax(0,1.4fr)]">
        <form className="panel" onSubmit={handleSubmit}>
          <h2 className="panel-title mt-0">{t("context.configuration")}</h2>

          <label
            htmlFor="context-messages"
            className="text-primary mt-6 block text-sm font-medium"
          >
            {t("context.messagesJson")}
          </label>
          <p className="text-muted mt-1 text-xs leading-5">
            {t("context.messagesHint")}
          </p>
          <textarea
            id="context-messages"
            rows={20}
            value={messagesJson}
            onChange={(event) => setMessagesJson(event.target.value)}
            spellCheck={false}
            className="workbench-input mt-3 w-full resize-y rounded-md border px-4 py-3 font-mono text-xs leading-6 outline-none"
          />

          <label
            htmlFor="context-strategy"
            className="text-primary mt-5 block text-sm font-medium"
          >
            {t("context.strategy")}
          </label>
          <select
            id="context-strategy"
            value={strategy}
            onChange={(event) =>
              setStrategy(event.target.value as ContextCompressionStrategy)
            }
            className="workbench-input mt-2 w-full rounded-md border px-3 py-2 text-sm outline-none"
          >
            {(Object.keys(strategyLabelKeys) as ContextCompressionStrategy[]).map(
              (value) => (
                <option key={value} value={value}>
                  {t(strategyLabelKeys[value])}
                </option>
              ),
            )}
          </select>

          <fieldset className="mt-5 grid gap-4 sm:grid-cols-2">
            <legend className="sr-only">{t("context.budget")}</legend>
            <div>
              <label
                htmlFor="context-target-budget"
                className="text-primary block text-sm font-medium"
              >
                {t("context.targetBudget")}
              </label>
              <input
                id="context-target-budget"
                type="number"
                min="1"
                step="1"
                value={targetBudget}
                onChange={(event) => setTargetBudget(event.target.value)}
                className="workbench-input mt-2 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none"
              />
              <p className="text-muted mt-1 text-xs leading-5">
                {t("context.targetBudgetHint")}
              </p>
            </div>
            <div>
              <label
                htmlFor="context-max-budget"
                className="text-primary block text-sm font-medium"
              >
                {t("context.maxBudget")}
              </label>
              <input
                id="context-max-budget"
                type="number"
                min="1"
                step="1"
                value={maxBudget}
                onChange={(event) => setMaxBudget(event.target.value)}
                className="workbench-input mt-2 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none"
              />
              <p className="text-muted mt-1 text-xs leading-5">
                {t("context.maxBudgetHint")}
              </p>
            </div>
          </fieldset>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm" aria-live="polite">
              {error ? (
                <p className="text-error">{t(errorLabelKeys[error])}</p>
              ) : null}
              {loading ? (
                <p className="text-accent">{t("context.compressing")}</p>
              ) : null}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="primary-action rounded-md border px-4 py-2 text-sm font-medium"
            >
              {loading ? t("context.compressing") : t("context.compress")}
            </button>
          </div>

          <p className="text-muted mt-5 border-t pt-4 text-xs leading-5 [border-color:var(--border)]">
            {t("context.offlineNote")}
          </p>
        </form>

        <div className="space-y-4">
          <section className="panel" aria-labelledby="context-result-heading">
            <h2 id="context-result-heading" className="panel-title mt-0">
              {t("context.result")}
            </h2>
            <p className="text-muted mt-2 text-xs leading-5">
              {t("context.estimateNote")}
            </p>
            {result ? (
              <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {metrics.map(([label, value]) => (
                  <div key={label} className="metric-card rounded-md p-3">
                    <dt className="text-muted text-[11px]">{label}</dt>
                    <dd className="text-secondary mt-2 font-mono text-sm">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-muted mt-5 text-sm">
                {t("context.emptyResult")}
              </p>
            )}
          </section>

          {result ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <section
                className="panel min-w-0"
                aria-labelledby="original-messages-heading"
              >
                <h2
                  id="original-messages-heading"
                  className="panel-title mt-0"
                >
                  {t("context.originalMessages")}
                </h2>
                <MessageList
                  messages={result.original_messages}
                  emptyLabel={t("context.emptyMessages")}
                />
              </section>

              <section
                className="panel min-w-0"
                aria-labelledby="compressed-messages-heading"
              >
                <h2
                  id="compressed-messages-heading"
                  className="panel-title mt-0"
                >
                  {t("context.compressedMessages")}
                </h2>
                <MessageList
                  messages={result.compressed_messages}
                  emptyLabel={t("context.emptyMessages")}
                />
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
