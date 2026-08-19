export type RunStatus = "completed" | "failed" | "stopped";

export interface TraceEvent {
  sequence: number;
  event_type: string;
  name: string;
  detail: string | null;
}

export interface RunMetrics {
  iterations: number | null;
  tool_calls: number | null;
  duration_ms: number | null;
}

export interface SourceReference {
  title: string;
  url: string | null;
}

export interface RunResult {
  status: RunStatus;
  output: string | null;
  trace: TraceEvent[];
  metrics: RunMetrics;
  sources: SourceReference[];
  error: string | null;
}

export interface WebResearchRequest {
  query: string;
}

export type StreamEventType =
  | "started"
  | "trace"
  | "completed"
  | "stopped"
  | "error";

export interface StreamEvent {
  sequence: number;
  event_type: StreamEventType;
  data: Record<string, unknown>;
}

export type ContextMessageRole = "system" | "user" | "assistant" | "tool";

export interface ContextMessage {
  role: ContextMessageRole;
  content: string | null;
}

export type ContextCompressionStrategy =
  | "no_compression"
  | "truncation"
  | "windowed";

export interface ContextCompressionInput {
  messages: ContextMessage[];
  target_token_budget: number;
  max_token_budget: number;
  strategy: ContextCompressionStrategy;
}

export interface ContextCompressionResult {
  original_messages: ContextMessage[];
  compressed_messages: ContextMessage[];
  original_token_estimate: number;
  compressed_token_estimate: number;
  tokens_saved_estimate: number;
  compression_ratio: number;
  strategy: ContextCompressionStrategy;
  duration_ms: number;
  compression_applied: boolean;
  compressed_message_count: number;
  preserved_message_count: number;
}
