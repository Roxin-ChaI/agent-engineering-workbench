import {
  PROMPT_EXPERIMENT_VARIANTS,
  type PromptBundleInput,
  type PromptEvaluationSummary,
  type PromptExperimentMetrics,
  type PromptExperimentOptions,
  type PromptExperimentRequest,
  type PromptExperimentResult,
  type PromptSuccessCriteria,
  type PromptTaskInput,
} from "@/lib/contracts";

type Assert<T extends true> = T;
type IsNever<T> = [T] extends [never] ? true : false;

export const minimalPromptExperimentRequestFixture = {
  prompt: {
    system_prompt: "Follow the supplied policy exactly.",
    wiki_rules: ["Confirm details before answering."],
  },
  task: {
    task_id: "task-1",
    environment: "airline",
    instruction: "Confirm the baggage allowance.",
  },
} satisfies PromptExperimentRequest;

export const fullPromptExperimentRequestFixture = {
  prompt: {
    system_prompt: "Follow the supplied policy exactly.",
    wiki_rules: ["Confirm details before answering."],
  },
  task: {
    task_id: "task-1",
    environment: "retail",
    instruction: "Confirm the return policy.",
    success_criteria: {
      require_final_response: true,
      exact_response: null,
      required_response_substrings: ["30 days"],
      forbidden_response_substrings: ["unknown"],
      required_tool_names: [],
      forbidden_tool_names: ["cancel_order"],
    },
  },
  variant: "tone_casual",
  options: {
    max_steps: 12,
    seed: 7,
  },
} satisfies PromptExperimentRequest;

export const promptExperimentSuccessResultFixture = {
  task_id: "task-1",
  variant: "baseline",
  final_response: "The allowance is confirmed.",
  reward: 1,
  completed: true,
  evaluation: {
    reward: 1,
    completed: true,
    criteria_total: 1,
    criteria_passed: 1,
    criteria_failed: 0,
  },
  metrics: {
    step_count: 1,
    tool_call_count: 0,
  },
} satisfies PromptExperimentResult;

export const promptExperimentFailedEvaluationFixture = {
  task_id: "task-1",
  variant: "wiki_random",
  final_response: "The requested criterion was not satisfied.",
  reward: 0,
  completed: false,
  evaluation: {
    reward: 0,
    completed: false,
    criteria_total: 2,
    criteria_passed: 1,
    criteria_failed: 1,
  },
  metrics: {
    step_count: 2,
    tool_call_count: 0,
  },
} satisfies PromptExperimentResult;

type ProviderSecretNames =
  | "api_key"
  | "deepseek_api_key"
  | "provider_secret"
  | "base_url"
  | "model_client";

type PromptContractKeys =
  | keyof PromptExperimentRequest
  | keyof PromptBundleInput
  | keyof PromptTaskInput
  | keyof PromptSuccessCriteria
  | keyof PromptExperimentOptions
  | keyof PromptExperimentResult
  | keyof PromptEvaluationSummary
  | keyof PromptExperimentMetrics;

export type PromptContractHasNoProviderSecrets = Assert<
  IsNever<Extract<PromptContractKeys, ProviderSecretNames>>
>;

export type PromptExperimentHasSixVariants = Assert<
  (typeof PROMPT_EXPERIMENT_VARIANTS)["length"] extends 6 ? true : false
>;
