import inspect
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_engineering_workbench import dependencies
from agent_engineering_workbench.app import app
from agent_engineering_workbench.dependencies import get_prompt_library_backend
from agent_engineering_workbench.prompt_library_contracts import (
    PromptLibraryCreateRequest,
    PromptLibraryItem,
    PromptLibraryList,
    PromptLibrarySearchRequest,
    PromptLibraryUpdateRequest,
)
from agent_engineering_workbench.prompt_library_errors import (
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROMPT_LIBRARY_SOURCE = (
    REPOSITORY_ROOT / "frontend/src/components/prompt-library-panel.tsx"
)
PROMPT_WORKSPACE_SOURCE = (
    REPOSITORY_ROOT
    / "frontend/src/components/prompt-experiment-workspace.tsx"
)
PROMPT_LIBRARY_STATE_SOURCE = (
    REPOSITORY_ROOT / "frontend/src/lib/prompt-library-workspace-state.ts"
)
FRONTEND_API_SOURCE = REPOSITORY_ROOT / "frontend/src/lib/api.ts"


def make_item(
    *,
    prompt_id: int = 1,
    title: str = "Existing Prompt",
    content: str = "Use the existing grounded policy.",
    wiki_rules: list[str] | None = None,
    tags: list[str] | None = None,
) -> PromptLibraryItem:
    return PromptLibraryItem(
        id=prompt_id,
        title=title,
        content=content,
        wiki_rules=(
            ["Existing rule A", "Existing rule B"]
            if wiki_rules is None
            else wiki_rules
        ),
        tags=["existing", "grounded"] if tags is None else tags,
    )


class InMemoryPromptLibraryBackend:
    """Deterministic test-only fake at the Workbench backend Protocol boundary."""

    def __init__(self) -> None:
        self.items = [
            make_item(),
            make_item(
                prompt_id=2,
                title="No Rules Prompt",
                content="Use the no-rules policy.",
                wiki_rules=[],
                tags=["empty-rules"],
            ),
        ]
        self.next_id = 3
        self.calls: list[tuple[str, object]] = []
        self.failures: dict[str, Exception] = {}

    def fail_next(self, operation: str, error: Exception) -> None:
        self.failures[operation] = error

    def _record(self, operation: str, value: object) -> None:
        self.calls.append((operation, value))
        error = self.failures.pop(operation, None)
        if error is not None:
            raise error

    def _item_index(self, prompt_id: int) -> int:
        for index, item in enumerate(self.items):
            if item.id == prompt_id:
                return index
        raise PromptLibraryNotFoundError("fake prompt does not exist")

    def create_prompt(
        self,
        request: PromptLibraryCreateRequest,
    ) -> PromptLibraryItem:
        self._record("create", request)
        item = PromptLibraryItem(id=self.next_id, **request.model_dump())
        self.next_id += 1
        self.items.append(item)
        return item

    def list_prompts(self) -> PromptLibraryList:
        self._record("list", None)
        return list(self.items)

    def get_prompt(self, prompt_id: int) -> PromptLibraryItem:
        self._record("get", prompt_id)
        return self.items[self._item_index(prompt_id)]

    def search_prompts(
        self,
        request: PromptLibrarySearchRequest,
    ) -> PromptLibraryList:
        self._record("search", request)
        query = request.q.casefold()
        return [
            item
            for item in self.items
            if query in item.title.casefold() or query in item.content.casefold()
        ]

    def update_prompt(
        self,
        prompt_id: int,
        request: PromptLibraryUpdateRequest,
    ) -> PromptLibraryItem:
        self._record("update", (prompt_id, request))
        index = self._item_index(prompt_id)
        changes = request.model_dump(exclude_unset=True, exclude_none=True)
        updated = self.items[index].model_copy(update=changes)
        self.items[index] = updated
        return updated

    def delete_prompt(self, prompt_id: int) -> None:
        self._record("delete", prompt_id)
        self.items.pop(self._item_index(prompt_id))


@pytest.fixture
def fake_backend() -> Iterator[InMemoryPromptLibraryBackend]:
    backend = InMemoryPromptLibraryBackend()
    app.dependency_overrides[get_prompt_library_backend] = lambda: backend
    yield backend
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_backend: InMemoryPromptLibraryBackend) -> TestClient:
    del fake_backend
    return TestClient(app, raise_server_exceptions=False)


def test_initial_list_keeps_library_and_experiment_workspace_visible(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    response = client.get("/api/prompts/library")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == [
        "Existing Prompt",
        "No Rules Prompt",
    ]
    assert fake_backend.calls == [("list", None)]
    assert "PromptLibraryPanel" in PROMPT_WORKSPACE_SOURCE.read_text()
    assert 'aria-labelledby="experiment-heading"' in (
        PROMPT_WORKSPACE_SOURCE.read_text()
    )


def test_save_preserves_prompt_bundle_and_ordered_tags(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    payload = {
        "title": "Grounded Research",
        "content": "You are a grounded research assistant.",
        "wiki_rules": ["Rule A", "Rule B"],
        "tags": ["research", "grounding"],
    }

    response = client.post("/api/prompts/library", json=payload)

    assert response.status_code == 201
    assert response.json() == {"id": 3, **payload}
    assert fake_backend.items[-1].model_dump(mode="json") == {
        "id": 3,
        **payload,
    }
    assert fake_backend.calls == [
        ("create", PromptLibraryCreateRequest.model_validate(payload))
    ]
    library_source = PROMPT_LIBRARY_SOURCE.read_text()
    assert "upsertPromptLibraryItem(currentItems, created)" in library_source
    assert "items.map((item)" in library_source


def test_search_is_case_insensitive_title_content_only_and_clear_lists_all(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    fake_backend.items.append(
        make_item(
            prompt_id=3,
            title="Unrelated",
            content="Grounded content marker.",
            wiki_rules=["Grounded must not be searched here."],
            tags=["Grounded must not be searched here."],
        )
    )
    fake_backend.items.append(
        make_item(
            prompt_id=4,
            title="Rule-only match",
            content="No matching content.",
            wiki_rules=["Grounded"],
            tags=["Grounded"],
        )
    )

    search_response = client.get(
        "/api/prompts/library/search",
        params={"q": "GROUNDED"},
    )
    list_response = client.get("/api/prompts/library")

    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()] == [1, 3]
    assert [item["id"] for item in list_response.json()] == [1, 2, 3, 4]
    assert [operation for operation, _value in fake_backend.calls] == [
        "search",
        "list",
    ]
    library_source = PROMPT_LIBRARY_SOURCE.read_text()
    assert "searchPromptLibraryItems(query)" in library_source
    assert "void loadAllPrompts()" in library_source


def test_load_and_empty_rules_change_only_prompt_bundle_fields(
    client: TestClient,
) -> None:
    response = client.get("/api/prompts/library/2")
    workspace_source = PROMPT_WORKSPACE_SOURCE.read_text()
    state_source = PROMPT_LIBRARY_STATE_SOURCE.read_text()

    assert response.status_code == 200
    assert response.json()["wiki_rules"] == []
    load_callback = workspace_source.split("onLoadPrompt=", maxsplit=1)[1].split(
        "/>", maxsplit=1
    )[0]
    assert "setSystemPrompt(item.content)" in load_callback
    assert "setWikiRules(promptLibraryRulesToText(item.wiki_rules))" in load_callback
    assert 'return rules.join("\\n")' in state_source
    for forbidden_setter in (
        "setTaskId",
        "setInstruction",
        "setVariant",
        "setMaxSteps",
        "setSeed",
        "setResult",
    ):
        assert forbidden_setter not in load_callback


def test_update_full_prompt_preserves_order_and_updates_visible_record(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    payload = {
        "title": "Updated Grounded Research",
        "content": "Use the updated grounded policy.",
        "wiki_rules": ["Updated rule B", "Updated rule A"],
        "tags": ["updated", "research"],
    }

    response = client.put("/api/prompts/library/1", json=payload)

    assert response.status_code == 200
    assert response.json() == {"id": 1, **payload}
    assert fake_backend.items[0].model_dump(mode="json") == {
        "id": 1,
        **payload,
    }
    assert "upsertPromptLibraryItem(currentItems, updated)" in (
        PROMPT_LIBRARY_SOURCE.read_text()
    )


def test_update_distinguishes_omitted_and_explicit_empty_rules(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    omitted_response = client.put(
        "/api/prompts/library/1",
        json={"title": "Title only update"},
    )

    assert omitted_response.status_code == 200
    assert omitted_response.json()["title"] == "Title only update"
    assert omitted_response.json()["wiki_rules"] == [
        "Existing rule A",
        "Existing rule B",
    ]
    clear_response = client.put(
        "/api/prompts/library/1",
        json={"wiki_rules": []},
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["wiki_rules"] == []
    operation, captured = fake_backend.calls[1]
    assert operation == "update"
    assert isinstance(captured, tuple)
    assert captured[1].wiki_rules == []
    assert "wiki_rules" in captured[1].model_fields_set


def test_confirmed_delete_removes_only_library_state(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    response = client.delete("/api/prompts/library/1")
    library_source = PROMPT_LIBRARY_SOURCE.read_text()
    state_source = PROMPT_LIBRARY_STATE_SOURCE.read_text()

    assert response.status_code == 204
    assert [item.id for item in fake_backend.items] == [2]
    assert 'window.confirm(t("prompt.libraryDeleteConfirm"))' in library_source
    assert "selectedPromptAfterDelete(currentId, item.id)" in library_source
    assert "selectedPromptId === deletedPromptId ? null" in state_source
    assert "onLoadPrompt(item)" not in library_source.split(
        "async function handleDelete", maxsplit=1
    )[1]


def test_library_error_is_safe_and_experiment_form_remains_independent(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    fake_backend.fail_next(
        "list",
        PromptLibraryUpstreamError("private vault transport detail"),
    )

    response = client.get("/api/prompts/library")
    library_source = PROMPT_LIBRARY_SOURCE.read_text()
    workspace_source = PROMPT_WORKSPACE_SOURCE.read_text()

    assert response.status_code == 502
    assert response.json() == {"detail": "Prompt library service is unavailable."}
    assert "private" not in response.text
    assert 'status === "502"' in library_source
    assert 'aria-busy={listLoading}' in library_source
    assert 'aria-busy={loading}' in workspace_source
    assert "setLoading(" not in library_source


def test_mutation_failure_is_single_attempt_and_does_not_mutate_store(
    client: TestClient,
    fake_backend: InMemoryPromptLibraryBackend,
) -> None:
    requests = (
        (
            "create",
            lambda: client.post(
                "/api/prompts/library",
                json={"title": "Failed", "content": "Must not persist."},
            ),
        ),
        (
            "update",
            lambda: client.put(
                "/api/prompts/library/1",
                json={"title": "Must not replace"},
            ),
        ),
        ("delete", lambda: client.delete("/api/prompts/library/1")),
    )

    for operation, request in requests:
        original_items = list(fake_backend.items)
        fake_backend.calls.clear()
        fake_backend.fail_next(
            operation,
            PromptLibraryUpstreamError("private mutation failure"),
        )

        response = request()

        assert response.status_code == 502
        assert fake_backend.items == original_items
        assert [name for name, _value in fake_backend.calls] == [operation]


def test_selected_item_404_maps_to_stable_frontend_error() -> None:
    backend = InMemoryPromptLibraryBackend()
    app.dependency_overrides[get_prompt_library_backend] = lambda: backend
    backend.fail_next("update", PromptLibraryNotFoundError("private missing id"))
    try:
        response = TestClient(app, raise_server_exceptions=False).put(
            "/api/prompts/library/1",
            json={"title": "Missing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Prompt library item was not found."}
    assert "private" not in response.text
    assert 'status === "404"' in PROMPT_LIBRARY_SOURCE.read_text()


def test_request_fidelity_and_experiment_request_regression() -> None:
    library_source = PROMPT_LIBRARY_SOURCE.read_text()
    workspace_source = PROMPT_WORKSPACE_SOURCE.read_text()

    create_payload = library_source.split(
        "createPromptLibraryItem({", maxsplit=1
    )[1].split("});", maxsplit=1)[0]
    update_payload = library_source.split(
        "updatePromptLibraryItem(selectedPromptId, {", maxsplit=1
    )[1].split("});", maxsplit=1)[0]
    for payload in (create_payload, update_payload):
        assert all(
            field in payload
            for field in ("title:", "content:", "wiki_rules:", "tags:")
        )
        assert all(
            field not in payload
            for field in (
                "task",
                "criteria",
                "variant",
                "max_steps",
                "maxSteps",
                "seed",
                "result",
            )
        )

    experiment_payload = workspace_source.split(
        "const request: PromptExperimentRequest = {", maxsplit=1
    )[1].split("inFlight.current = true", maxsplit=1)[0]
    assert "selectedPromptId" not in experiment_payload
    assert "library" not in experiment_payload.casefold()
    assert workspace_source.count("await runPromptExperiment(request)") == 1


def test_fake_protocol_boundary_has_no_network_database_or_secret_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROMPT_VAULT_BASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        dependencies,
        "PromptVaultHttpClient",
        lambda *_args, **_kwargs: pytest.fail(
            "production Prompt Vault HTTP client must not be created"
        ),
    )
    backend = InMemoryPromptLibraryBackend()
    app.dependency_overrides[get_prompt_library_backend] = lambda: backend
    try:
        response = TestClient(app).get("/api/prompts/library")
    finally:
        app.dependency_overrides.clear()

    fake_source = inspect.getsource(InMemoryPromptLibraryBackend)
    frontend_api_source = FRONTEND_API_SOURCE.read_text()

    assert response.status_code == 200
    assert all(
        forbidden not in fake_source
        for forbidden in (
            "PromptVaultHttpClient",
            "httpx",
            "requests",
            "sqlite",
            "DATABASE_URL",
            "PROMPT_VAULT_BASE_URL",
        )
    )
    assert all(
        endpoint in frontend_api_source
        for endpoint in (
            '"/api/prompts/library"',
            '`/api/prompts/library/${encodeURIComponent(String(id))}`',
            '`/api/prompts/library/search?${query.toString()}`',
        )
    )
    assert "PROMPT_VAULT_BASE_URL" not in frontend_api_source
    assert "DATABASE_URL" not in frontend_api_source
    assert "PromptVaultHttpClient" not in frontend_api_source
    assert all(
        retry_token not in PROMPT_LIBRARY_SOURCE.read_text()
        for retry_token in ("setTimeout", "setInterval", "retry")
    )
