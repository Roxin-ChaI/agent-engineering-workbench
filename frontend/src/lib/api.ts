import type {
  ContextCompressionInput,
  ContextCompressionResult,
  GitHubReviewRequest,
  GitHubReviewResult,
  PromptExperimentRequest,
  PromptExperimentResult,
  ResumeOptimizationResult,
  RunResult,
  StreamEvent,
  StreamEventType,
  WebResearchRequest,
} from "@/lib/contracts";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function getApiBaseUrl(): string {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return (configuredBaseUrl || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export async function runWebResearch(query: string): Promise<RunResult> {
  return runResearch("/api/research/web", "Web research", query);
}

export async function runKnowledgeResearch(
  query: string,
): Promise<RunResult> {
  return runResearch("/api/research/knowledge", "Knowledge research", query);
}

export async function compressContext(
  request: ContextCompressionInput,
): Promise<ContextCompressionResult> {
  return postJson(
    "/api/context/compress",
    "Context compression",
    request,
  );
}

export async function reviewPullRequest(
  prUrl: string,
): Promise<GitHubReviewResult> {
  const normalizedPrUrl = prUrl.trim();
  if (!normalizedPrUrl) {
    throw new Error("Pull Request URL must not be empty");
  }

  const request: GitHubReviewRequest = { pr_url: normalizedPrUrl };
  return postJson("/api/github/review", "GitHub review", request);
}

export async function optimizeResume(
  resume: File,
  jobDescription: string,
): Promise<ResumeOptimizationResult> {
  const formData = new FormData();
  formData.append("resume", resume);
  formData.append("job_description", jobDescription);
  return post("/api/resume/optimize", "Resume optimization", formData);
}

export async function runPromptExperiment(
  request: PromptExperimentRequest,
): Promise<PromptExperimentResult> {
  return postJson(
    "/api/prompts/experiment",
    "Prompt experiment",
    request,
  );
}

async function runResearch(
  path: string,
  requestName: string,
  query: string,
): Promise<RunResult> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    throw new Error("Research query must not be empty");
  }

  const request: WebResearchRequest = { query: normalizedQuery };
  return postJson(path, requestName, request);
}

async function postJson<Result>(
  path: string,
  requestName: string,
  body: unknown,
): Promise<Result> {
  return post(path, requestName, JSON.stringify(body), {
    "Content-Type": "application/json",
  });
}

async function post<Result>(
  path: string,
  requestName: string,
  body: BodyInit,
  headers?: HeadersInit,
): Promise<Result> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers,
    body,
  });

  if (!response.ok) {
    throw new Error(`${requestName} request failed with status ${response.status}`);
  }

  return (await response.json()) as Result;
}

const streamEventTypes = new Set<StreamEventType>([
  "started",
  "trace",
  "completed",
  "stopped",
  "error",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStreamEventType(value: string): value is StreamEventType {
  return streamEventTypes.has(value as StreamEventType);
}

function parseSseEvent(block: string): StreamEvent {
  let eventType: string | null = null;
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      if (eventType !== null) {
        throw new Error("Invalid web research stream event");
      }
      eventType = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    } else if (line.trim()) {
      throw new Error("Invalid web research stream event");
    }
  }

  if (!eventType || !isStreamEventType(eventType) || dataLines.length === 0) {
    throw new Error("Invalid web research stream event");
  }

  let payload: unknown;
  try {
    payload = JSON.parse(dataLines.join("\n"));
  } catch {
    throw new Error("Invalid web research stream event data");
  }

  if (
    !isRecord(payload) ||
    !Number.isInteger(payload.sequence) ||
    (payload.sequence as number) < 0 ||
    !isRecord(payload.data)
  ) {
    throw new Error("Invalid web research stream event data");
  }

  return {
    sequence: payload.sequence as number,
    event_type: eventType,
    data: payload.data,
  };
}

export async function streamWebResearch(
  query: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  return streamResearch(
    "/api/research/web/stream",
    "Web research",
    query,
    onEvent,
  );
}

export async function streamKnowledgeResearch(
  query: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  return streamResearch(
    "/api/research/knowledge/stream",
    "Knowledge research",
    query,
    onEvent,
  );
}

async function streamResearch(
  path: string,
  requestName: string,
  query: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    throw new Error("Research query must not be empty");
  }

  const request: WebResearchRequest = { query: normalizedQuery };
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`${requestName} stream failed with status ${response.status}`);
  }
  if (!response.body) {
    throw new Error(`${requestName} stream response body is unavailable`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replaceAll("\r\n", "\n");

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const block = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      if (block.trim()) {
        onEvent(parseSseEvent(block));
      }
      boundaryIndex = buffer.indexOf("\n\n");
    }
  }

  buffer = buffer.replaceAll("\r\n", "\n");
  if (buffer.trim()) {
    onEvent(parseSseEvent(buffer));
  }
}
