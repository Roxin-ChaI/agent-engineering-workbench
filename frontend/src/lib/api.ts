import type { RunResult, WebResearchRequest } from "@/lib/contracts";

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
