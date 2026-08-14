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
