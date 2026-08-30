"use client";

import { type FormEvent, useRef, useState } from "react";

import { PromptLibraryPanel } from "@/components/prompt-library-panel";
import { usePreferences } from "@/components/preferences-provider";
import { runPromptExperiment } from "@/lib/api";
import {
  PROMPT_EXPERIMENT_VARIANTS,
  type PromptExperimentEnvironment,
  type PromptExperimentRequest,
  type PromptExperimentResult,
  type PromptExperimentVariant,
  type PromptLibraryItem,
} from "@/lib/contracts";
import { promptLibraryRulesToText } from "@/lib/prompt-library-workspace-state";
import type { TranslationKey } from "@/lib/i18n";

const variantLabelKeys: Record<PromptExperimentVariant, TranslationKey> = {
  baseline: "prompt.variantBaseline",
  tone_trump: "prompt.variantToneTrump",
  tone_casual: "prompt.variantToneCasual",
  wiki_random: "prompt.variantWikiRandom",
  no_tool_desc: "prompt.variantNoToolDescription",
  all_ablations: "prompt.variantAllAblations",
};

const environmentLabelKeys: Record<
  PromptExperimentEnvironment,
  TranslationKey
> = {
  airline: "prompt.environmentAirline",
  retail: "prompt.environmentRetail",
};

type FormError =
  | "systemPromptRequired"
  | "wikiRulesRequired"
  | "taskIdRequired"
  | "instructionRequired"
  | "invalidOptions"
  | "toolsUnavailable"
  | "invalidRequest"
  | "providerFailure"
  | "executionFailure"
  | "networkFailure";

const errorLabelKeys: Record<FormError, TranslationKey> = {
  systemPromptRequired: "prompt.systemPromptRequired",
  wikiRulesRequired: "prompt.wikiRulesRequired",
  taskIdRequired: "prompt.taskIdRequired",
  instructionRequired: "prompt.instructionRequired",
  invalidOptions: "prompt.invalidOptions",
  toolsUnavailable: "prompt.toolsUnavailableError",
  invalidRequest: "prompt.invalidRequest",
  providerFailure: "prompt.providerFailure",
  executionFailure: "prompt.executionFailure",
  networkFailure: "prompt.networkFailure",
};

function splitLines(value: string): string[] {
  return value
    .split(/\r?\n/u)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function errorStatus(error: unknown): string | null {
  if (!(error instanceof Error)) {
    return null;
  }
  return error.message.match(/status (\d{3})/u)?.[1] ?? null;
}

function CriteriaListField({
  id,
  label,
  hint,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-primary block text-sm font-medium">
        {label}
      </label>
      <p className="text-muted mt-1 text-xs leading-5">{hint}</p>
      <textarea
        id={id}
        rows={3}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="prompt-placeholder workbench-input mt-2 w-full resize-y rounded-md border px-3 py-2 font-mono text-xs leading-5 outline-none"
      />
    </div>
  );
}

export function PromptExperimentWorkspace() {
  const { t } = usePreferences();
  const [systemPrompt, setSystemPrompt] = useState("");
  const [wikiRules, setWikiRules] = useState("");
  const [taskId, setTaskId] = useState("");
  const [environment, setEnvironment] =
    useState<PromptExperimentEnvironment>("airline");
  const [instruction, setInstruction] = useState("");
  const [requireFinalResponse, setRequireFinalResponse] = useState(true);
  const [exactResponse, setExactResponse] = useState("");
  const [requiredSubstrings, setRequiredSubstrings] = useState("");
  const [forbiddenSubstrings, setForbiddenSubstrings] = useState("");
  const [requiredTools, setRequiredTools] = useState("");
  const [forbiddenTools, setForbiddenTools] = useState("");
  const [variant, setVariant] =
    useState<PromptExperimentVariant>("baseline");
  const [maxSteps, setMaxSteps] = useState("30");
  const [seed, setSeed] = useState("0");
  const [result, setResult] = useState<PromptExperimentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<FormError | null>(null);
  const inFlight = useRef(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || inFlight.current) {
      return;
    }

    const normalizedSystemPrompt = systemPrompt.trim();
    const normalizedTaskId = taskId.trim();
    const normalizedInstruction = instruction.trim();
    const normalizedWikiRules = splitLines(wikiRules);
    const normalizedRequiredTools = splitLines(requiredTools);
    const numericMaxSteps = Number(maxSteps);
    const numericSeed = Number(seed);

    setError(null);
    if (!normalizedSystemPrompt) {
      setError("systemPromptRequired");
      return;
    }
    if (normalizedWikiRules.length === 0) {
      setError("wikiRulesRequired");
      return;
    }
    if (!normalizedTaskId) {
      setError("taskIdRequired");
      return;
    }
    if (!normalizedInstruction) {
      setError("instructionRequired");
      return;
    }
    if (
      !Number.isInteger(numericMaxSteps) ||
      numericMaxSteps <= 0 ||
      !Number.isInteger(numericSeed) ||
      numericSeed < 0
    ) {
      setError("invalidOptions");
      return;
    }
    if (normalizedRequiredTools.length > 0) {
      setError("toolsUnavailable");
      return;
    }

    const request: PromptExperimentRequest = {
      prompt: {
        system_prompt: normalizedSystemPrompt,
        wiki_rules: normalizedWikiRules,
      },
      task: {
        task_id: normalizedTaskId,
        environment,
        instruction: normalizedInstruction,
        success_criteria: {
          require_final_response: requireFinalResponse,
          exact_response: exactResponse.trim() || null,
          required_response_substrings: splitLines(requiredSubstrings),
          forbidden_response_substrings: splitLines(forbiddenSubstrings),
          required_tool_names: normalizedRequiredTools,
          forbidden_tool_names: splitLines(forbiddenTools),
        },
      },
      variant,
      options: {
        max_steps: numericMaxSteps,
        seed: numericSeed,
      },
    };

    inFlight.current = true;
    setResult(null);
    setLoading(true);
    try {
      setResult(await runPromptExperiment(request));
    } catch (requestError) {
      const status = errorStatus(requestError);
      if (status === "422") {
        setError("invalidRequest");
      } else if (status === "502") {
        setError("providerFailure");
      } else if (status === "500") {
        setError("executionFailure");
      } else {
        setError("networkFailure");
      }
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }

  const resultStatusKey: TranslationKey | null = result
    ? result.completed
      ? "prompt.evaluationPass"
      : "prompt.evaluationFailed"
    : null;

  return (
    <section className="mx-auto max-w-7xl">
      <p className="section-label">{t("prompt.section")}</p>
      <h1 className="page-title">{t("prompt.title")}</h1>
      <p className="page-description">{t("prompt.description")}</p>

      <PromptLibraryPanel
        systemPrompt={systemPrompt}
        wikiRules={wikiRules}
        onLoadPrompt={(item: PromptLibraryItem) => {
          setSystemPrompt(item.content);
          setWikiRules(promptLibraryRulesToText(item.wiki_rules));
        }}
      />

      <form className="mt-8 space-y-4" aria-busy={loading} onSubmit={handleSubmit}>
        <div className="grid gap-4 xl:grid-cols-2">
          <section className="panel min-w-0" aria-labelledby="prompt-heading">
            <h2 id="prompt-heading" className="panel-title mt-0">
              {t("prompt.prompt")}
            </h2>

            <label
              htmlFor="prompt-system"
              className="text-primary mt-5 block text-sm font-medium"
            >
              {t("prompt.systemPrompt")}
            </label>
            <textarea
              id="prompt-system"
              rows={7}
              placeholder={t("prompt.systemPromptPlaceholder")}
              value={systemPrompt}
              onChange={(event) => setSystemPrompt(event.target.value)}
              className="prompt-placeholder workbench-input mt-2 w-full resize-y rounded-md border px-4 py-3 text-sm leading-6 outline-none"
            />

            <label
              htmlFor="prompt-wiki-rules"
              className="text-primary mt-5 block text-sm font-medium"
            >
              {t("prompt.wikiRules")}
            </label>
            <p className="text-muted mt-1 text-xs leading-5">
              {t("prompt.onePerLine")}
            </p>
            <textarea
              id="prompt-wiki-rules"
              rows={5}
              placeholder={t("prompt.wikiRulesPlaceholder")}
              value={wikiRules}
              onChange={(event) => setWikiRules(event.target.value)}
              className="prompt-placeholder workbench-input mt-2 w-full resize-y rounded-md border px-4 py-3 font-mono text-xs leading-6 outline-none"
            />
          </section>

          <section className="panel min-w-0" aria-labelledby="task-heading">
            <h2 id="task-heading" className="panel-title mt-0">
              {t("prompt.task")}
            </h2>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="prompt-task-id"
                  className="text-primary block text-sm font-medium"
                >
                  {t("prompt.taskId")}
                </label>
                <input
                  id="prompt-task-id"
                  type="text"
                  placeholder={t("prompt.taskIdPlaceholder")}
                  value={taskId}
                  onChange={(event) => setTaskId(event.target.value)}
                  className="prompt-placeholder workbench-input mt-2 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none"
                />
              </div>
              <div>
                <label
                  htmlFor="prompt-environment"
                  className="text-primary block text-sm font-medium"
                >
                  {t("prompt.environment")}
                </label>
                <select
                  id="prompt-environment"
                  value={environment}
                  onChange={(event) =>
                    setEnvironment(
                      event.target.value as PromptExperimentEnvironment,
                    )
                  }
                  className="workbench-input mt-2 w-full rounded-md border px-3 py-2 text-sm outline-none"
                >
                  {(Object.keys(environmentLabelKeys) as PromptExperimentEnvironment[]).map(
                    (value) => (
                      <option key={value} value={value}>
                        {t(environmentLabelKeys[value])}
                      </option>
                    ),
                  )}
                </select>
              </div>
            </div>

            <label
              htmlFor="prompt-instruction"
              className="text-primary mt-5 block text-sm font-medium"
            >
              {t("prompt.instruction")}
            </label>
            <textarea
              id="prompt-instruction"
              rows={7}
              placeholder={t("prompt.instructionPlaceholder")}
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              className="prompt-placeholder workbench-input mt-2 w-full resize-y rounded-md border px-4 py-3 text-sm leading-6 outline-none"
            />
          </section>
        </div>

        <section className="panel" aria-labelledby="criteria-heading">
          <h2 id="criteria-heading" className="panel-title mt-0">
            {t("prompt.successCriteria")}
          </h2>

          <label className="text-primary mt-5 flex items-center gap-3 text-sm font-medium">
            <input
              type="checkbox"
              checked={requireFinalResponse}
              onChange={(event) => setRequireFinalResponse(event.target.checked)}
              className="h-4 w-4 accent-[var(--accent)]"
            />
            {t("prompt.requireFinalResponse")}
          </label>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div>
              <label
                htmlFor="prompt-exact-response"
                className="text-primary block text-sm font-medium"
              >
                {t("prompt.exactResponse")}
              </label>
              <p className="text-muted mt-1 text-xs leading-5">
                {t("prompt.optional")}
              </p>
              <textarea
                id="prompt-exact-response"
                rows={3}
                placeholder={t("prompt.exactResponsePlaceholder")}
                value={exactResponse}
                onChange={(event) => setExactResponse(event.target.value)}
                className="prompt-placeholder workbench-input mt-2 w-full resize-y rounded-md border px-3 py-2 text-sm leading-5 outline-none"
              />
            </div>
            <CriteriaListField
              id="prompt-required-substrings"
              label={t("prompt.requiredSubstrings")}
              hint={t("prompt.onePerLine")}
              placeholder={t("prompt.requiredSubstringsPlaceholder")}
              value={requiredSubstrings}
              onChange={setRequiredSubstrings}
            />
            <CriteriaListField
              id="prompt-forbidden-substrings"
              label={t("prompt.forbiddenSubstrings")}
              hint={t("prompt.onePerLine")}
              placeholder={t("prompt.forbiddenSubstringsPlaceholder")}
              value={forbiddenSubstrings}
              onChange={setForbiddenSubstrings}
            />
            <div>
              <CriteriaListField
                id="prompt-required-tools"
                label={t("prompt.requiredTools")}
                hint={t("prompt.onePerLine")}
                placeholder={t("prompt.requiredToolsPlaceholder")}
                value={requiredTools}
                onChange={setRequiredTools}
              />
              <p className="status-stopped mt-2 rounded-md border px-3 py-2 text-xs leading-5">
                {t("prompt.toolsUnavailable")}
              </p>
            </div>
            <CriteriaListField
              id="prompt-forbidden-tools"
              label={t("prompt.forbiddenTools")}
              hint={t("prompt.onePerLine")}
              placeholder={t("prompt.forbiddenToolsPlaceholder")}
              value={forbiddenTools}
              onChange={setForbiddenTools}
            />
          </div>
        </section>

        <section className="panel" aria-labelledby="experiment-heading">
          <h2 id="experiment-heading" className="panel-title mt-0">
            {t("prompt.experimentConfiguration")}
          </h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <div>
              <label
                htmlFor="prompt-variant"
                className="text-primary block text-sm font-medium"
              >
                {t("prompt.variant")}
              </label>
              <select
                id="prompt-variant"
                value={variant}
                onChange={(event) =>
                  setVariant(event.target.value as PromptExperimentVariant)
                }
                className="workbench-input mt-2 w-full rounded-md border px-3 py-2 text-sm outline-none"
              >
                {PROMPT_EXPERIMENT_VARIANTS.map((value) => (
                  <option key={value} value={value}>
                    {t(variantLabelKeys[value])}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="prompt-max-steps"
                className="text-primary block text-sm font-medium"
              >
                {t("prompt.maxSteps")}
              </label>
              <input
                id="prompt-max-steps"
                type="number"
                min="1"
                step="1"
                value={maxSteps}
                onChange={(event) => setMaxSteps(event.target.value)}
                className="workbench-input mt-2 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none"
              />
            </div>
            <div>
              <label
                htmlFor="prompt-seed"
                className="text-primary block text-sm font-medium"
              >
                {t("prompt.seed")}
              </label>
              <input
                id="prompt-seed"
                type="number"
                min="0"
                step="1"
                value={seed}
                onChange={(event) => setSeed(event.target.value)}
                className="workbench-input mt-2 w-full rounded-md border px-3 py-2 font-mono text-sm outline-none"
              />
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm" aria-live="polite">
              {error ? <p className="text-error">{t(errorLabelKeys[error])}</p> : null}
              {loading ? <p className="text-accent">{t("prompt.running")}</p> : null}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="primary-action rounded-md border px-4 py-2 text-sm font-medium"
            >
              {loading ? t("prompt.running") : t("prompt.run")}
            </button>
          </div>
        </section>
      </form>

      <section className="panel mt-4 min-w-0" aria-labelledby="result-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 id="result-heading" className="panel-title mt-0">
            {t("prompt.result")}
          </h2>
          {result && resultStatusKey ? (
            <span
              className={`${result.completed ? "status-completed" : "status-stopped"} rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider`}
            >
              {t(resultStatusKey)}
            </span>
          ) : null}
        </div>

        {result ? (
          <div className="mt-5 space-y-4">
            <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                [t("prompt.taskId"), result.task_id],
                [t("prompt.variant"), t(variantLabelKeys[result.variant])],
                [t("prompt.reward"), String(result.reward)],
                [t("prompt.completed"), result.completed ? t("prompt.yes") : t("prompt.no")],
                [
                  t("prompt.criteriaPassed"),
                  `${result.evaluation.criteria_passed} / ${result.evaluation.criteria_total}`,
                ],
                [t("prompt.criteriaFailed"), String(result.evaluation.criteria_failed)],
                [t("prompt.steps"), String(result.metrics.step_count)],
                [t("prompt.toolCalls"), String(result.metrics.tool_call_count)],
              ].map(([label, value]) => (
                <div key={label} className="metric-card min-w-0 rounded-md p-3">
                  <dt className="text-muted text-[11px]">{label}</dt>
                  <dd className="text-secondary mt-2 break-words font-mono text-sm">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(16rem,0.6fr)]">
              <article className="metric-card min-w-0 rounded-md p-4 sm:p-5">
                <h3 className="text-primary text-sm font-semibold">
                  {t("prompt.finalResponse")}
                </h3>
                <p className="text-secondary mt-3 whitespace-pre-wrap break-words text-sm leading-7">
                  {result.final_response ?? t("prompt.noFinalResponse")}
                </p>
              </article>
              <article className="metric-card rounded-md p-4 sm:p-5">
                <h3 className="text-primary text-sm font-semibold">
                  {t("prompt.evaluation")}
                </h3>
                <p className="text-muted mt-3 text-xs leading-5">
                  {result.completed
                    ? t("prompt.evaluationPassDescription")
                    : t("prompt.evaluationFailedDescription")}
                </p>
              </article>
            </div>
          </div>
        ) : (
          <p className="text-muted mt-5 text-sm">{t("prompt.emptyResult")}</p>
        )}
      </section>
    </section>
  );
}
