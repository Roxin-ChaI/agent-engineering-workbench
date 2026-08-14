import type {
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
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    throw new Error("Research query must not be empty");
  }

  const request: WebResearchRequest = { query: normalizedQuery };
  const response = await fetch(`${getApiBaseUrl()}/api/research/web`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Web research request failed with status ${response.status}`);
  }

  return (await response.json()) as RunResult;
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
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    throw new Error("Research query must not be empty");
  }

  const request: WebResearchRequest = { query: normalizedQuery };
  const response = await fetch(`${getApiBaseUrl()}/api/research/web/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(
      `Web research stream failed with status ${response.status}`,
    );
  }
  if (!response.body) {
    throw new Error("Web research stream response body is unavailable");
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
