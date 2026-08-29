import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";

import {
  createPromptLibraryItem,
  deletePromptLibraryItem,
  getPromptLibraryItem,
  listPromptLibraryItems,
  runPromptExperiment,
  searchPromptLibraryItems,
  updatePromptLibraryItem,
} from "../src/lib/api.ts";

const item = {
  id: 1,
  title: "Research Assistant",
  content: "Use sources carefully.",
  wiki_rules: ["First rule", "Second rule"],
  tags: ["research", "grounded"],
};

afterEach(() => {
  mock.restoreAll();
});

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

test("create sends the complete Workbench contract and parses the item", async () => {
  const calls = [];
  mock.method(globalThis, "fetch", async (url, init) => {
    calls.push({ url, init });
    return jsonResponse(item, 201);
  });

  const request = {
    title: "Research Assistant",
    content: "Use sources carefully.",
    wiki_rules: ["First rule", "Second rule"],
    tags: ["research", "grounded"],
  };
  const result = await createPromptLibraryItem(request);

  assert.deepEqual(result, item);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://127.0.0.1:8000/api/prompts/library");
  assert.equal(calls[0].init.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].init.body), request);
});

test("list returns the direct array without reordering", async () => {
  const payload = [item, { ...item, id: 2, title: "Summarizer" }];
  mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/prompts/library");
    assert.equal(init.method, "GET");
    return jsonResponse(payload);
  });

  assert.deepEqual(await listPromptLibraryItems(), payload);
});

test("get requests the Workbench item route", async () => {
  mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/prompts/library/42");
    assert.equal(init.method, "GET");
    return jsonResponse(item);
  });

  assert.deepEqual(await getPromptLibraryItem(42), item);
});

test("search encodes query parameters without changing their meaning", async () => {
  mock.method(globalThis, "fetch", async (input, init) => {
    const url = new URL(input);
    assert.equal(url.pathname, "/api/prompts/library/search");
    assert.equal(url.searchParams.get("q"), "research agent & tools");
    assert.equal(init.method, "GET");
    return jsonResponse([item]);
  });

  assert.deepEqual(
    await searchPromptLibraryItems("research agent & tools"),
    [item],
  );
});

test("update leaves omitted wiki_rules out of JSON", async () => {
  mock.method(globalThis, "fetch", async (_url, init) => {
    const body = JSON.parse(init.body);
    assert.deepEqual(body, { title: "Updated" });
    assert.equal(Object.hasOwn(body, "wiki_rules"), false);
    return jsonResponse(item);
  });

  await updatePromptLibraryItem(1, { title: "Updated" });
});

test("update preserves explicit empty wiki_rules", async () => {
  mock.method(globalThis, "fetch", async (_url, init) => {
    const body = JSON.parse(init.body);
    assert.deepEqual(body, { wiki_rules: [] });
    assert.equal(Object.hasOwn(body, "wiki_rules"), true);
    return jsonResponse(item);
  });

  await updatePromptLibraryItem(1, { wiki_rules: [] });
});

test("update preserves ordered non-empty wiki_rules", async () => {
  mock.method(globalThis, "fetch", async (_url, init) => {
    assert.deepEqual(JSON.parse(init.body), {
      wiki_rules: ["rule-a", "rule-b"],
    });
    return jsonResponse(item);
  });

  await updatePromptLibraryItem(1, {
    wiki_rules: ["rule-a", "rule-b"],
  });
});

test("delete accepts 204 without attempting JSON parsing", async () => {
  let jsonCalls = 0;
  mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/prompts/library/9");
    assert.equal(init.method, "DELETE");
    return {
      ok: true,
      status: 204,
      async json() {
        jsonCalls += 1;
        throw new Error("JSON must not be parsed");
      },
    };
  });

  assert.equal(await deletePromptLibraryItem(9), undefined);
  assert.equal(jsonCalls, 0);
});

for (const status of [422, 404, 502, 500]) {
  test(`Workbench HTTP ${status} uses the existing status error contract`, async () => {
    mock.method(globalThis, "fetch", async () =>
      jsonResponse({ detail: "safe Workbench error" }, status),
    );

    await assert.rejects(
      listPromptLibraryItems(),
      new Error(`Prompt library list request failed with status ${status}`),
    );
  });
}

test("transport failures are mapped safely and are not retried", async () => {
  let calls = 0;
  mock.method(globalThis, "fetch", async () => {
    calls += 1;
    throw new TypeError(
      "fetch http://internal-host failed with password=secret and raw stack",
    );
  });

  await assert.rejects(
    listPromptLibraryItems(),
    new Error("Prompt library list request failed"),
  );
  assert.equal(calls, 1);
});

test("Prompt Experiment request behavior remains unchanged", async () => {
  const result = {
    task_id: "task-1",
    variant: "baseline",
    final_response: "PASS",
    reward: 1,
    completed: true,
    evaluation: {
      reward: 1,
      completed: true,
      criteria_total: 1,
      criteria_passed: 1,
      criteria_failed: 0,
    },
    metrics: { step_count: 1, tool_call_count: 0 },
  };
  const request = {
    prompt: { system_prompt: "Return PASS.", wiki_rules: [] },
    task: {
      task_id: "task-1",
      environment: "airline",
      instruction: "Return PASS.",
    },
  };
  mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/prompts/experiment");
    assert.equal(init.method, "POST");
    assert.deepEqual(JSON.parse(init.body), request);
    return jsonResponse(result);
  });

  assert.deepEqual(await runPromptExperiment(request), result);
});
