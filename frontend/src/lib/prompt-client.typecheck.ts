import { runPromptExperiment } from "@/lib/api";
import type {
  PromptExperimentRequest,
  PromptExperimentResult,
} from "@/lib/contracts";

type Assert<T extends true> = T;
type Equal<Left, Right> =
  (<Value>() => Value extends Left ? 1 : 2) extends <Value>() =>
    Value extends Right ? 1 : 2
    ? true
    : false;

type ExpectedPromptExperimentClient = (
  request: PromptExperimentRequest,
) => Promise<PromptExperimentResult>;

export type PromptExperimentClientSignatureMatches = Assert<
  Equal<typeof runPromptExperiment, ExpectedPromptExperimentClient>
>;

export type PromptExperimentClientAcceptsOnlyRequestContract = Assert<
  Equal<Parameters<typeof runPromptExperiment>, [PromptExperimentRequest]>
>;

export type PromptExperimentClientReturnsResultContract = Assert<
  Equal<ReturnType<typeof runPromptExperiment>, Promise<PromptExperimentResult>>
>;
