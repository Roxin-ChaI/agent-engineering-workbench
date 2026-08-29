import inspect
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import agent_engineering_workbench.api.prompt as prompt_api
from agent_engineering_workbench import dependencies
from agent_engineering_workbench.app import app
from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.dependencies import get_prompt_library_backend
from agent_engineering_workbench.prompt_library_contracts import (
    PromptLibraryCreateRequest,
    PromptLibraryItem,
    PromptLibraryList,
    PromptLibrarySearchRequest,
    PromptLibraryUpdateRequest,
)
from agent_engineering_workbench.prompt_library_errors import (
    InvalidPromptLibraryInputError,
    PromptLibraryInternalError,
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
)


def make_item(
    *,
    prompt_id: int = 1,
    title: str = "Research Assistant",
) -> PromptLibraryItem:
    return PromptLibraryItem(
        id=prompt_id,
        title=title,
        content="You are a careful research assistant.",
        wiki_rules=["Cite evidence.", "Do not infer unsupported claims."],
        tags=["research", "grounded"],
    )


class FakePromptLibraryBackend:
    def __init__(self) -> None:
        self.items = [make_item(), make_item(prompt_id=2, title="Summarizer")]
        self.error: BaseException | None = None
        self.calls: list[tuple[str, object]] = []

    def _raise_error(self) -> None:
        if self.error is not None:
            raise self.error

    def create_prompt(
        self,
        request: PromptLibraryCreateRequest,
    ) -> PromptLibraryItem:
        self.calls.append(("create", request))
        self._raise_error()
        return self.items[0]

    def list_prompts(self) -> PromptLibraryList:
        self.calls.append(("list", None))
        self._raise_error()
        return self.items

    def get_prompt(self, prompt_id: int) -> PromptLibraryItem:
        self.calls.append(("get", prompt_id))
        self._raise_error()
        return self.items[0]

    def search_prompts(
        self,
        request: PromptLibrarySearchRequest,
    ) -> PromptLibraryList:
        self.calls.append(("search", request))
        self._raise_error()
        return self.items

    def update_prompt(
        self,
        prompt_id: int,
        request: PromptLibraryUpdateRequest,
    ) -> PromptLibraryItem:
        self.calls.append(("update", (prompt_id, request)))
        self._raise_error()
        return self.items[0]

    def delete_prompt(self, prompt_id: int) -> None:
        self.calls.append(("delete", prompt_id))
        self._raise_error()


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def install_fake_backend(backend: FakePromptLibraryBackend) -> None:
    app.dependency_overrides[get_prompt_library_backend] = lambda: backend


def test_create_returns_201_and_preserves_complete_request_and_response() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)
    payload = {
        "title": "Research Assistant",
        "content": "Use sources carefully.",
        "wiki_rules": ["First rule", "Second rule"],
        "tags": ["research", "grounded"],
    }

    response = TestClient(app).post("/api/prompts/library", json=payload)

    assert response.status_code == 201
    assert response.json() == make_item().model_dump(mode="json")
    assert backend.calls == [
        ("create", PromptLibraryCreateRequest.model_validate(payload))
    ]


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"title": "", "content": "Valid content"},
        {"title": 42, "content": "Valid content"},
        {
            "title": "Valid title",
            "content": "Valid content",
            "wiki_rules": ["   "],
        },
    ),
)
def test_create_invalid_http_body_returns_standard_422(
    payload: dict[str, object],
) -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).post("/api/prompts/library", json=payload)

    assert response.status_code == 422
    assert backend.calls == []


def test_list_returns_direct_ordered_array_and_calls_backend_once() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get("/api/prompts/library")

    assert response.status_code == 200
    assert response.json() == [item.model_dump(mode="json") for item in backend.items]
    assert backend.calls == [("list", None)]


def test_get_passes_integer_prompt_id_unchanged() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get("/api/prompts/library/42")

    assert response.status_code == 200
    assert response.json() == make_item().model_dump(mode="json")
    assert backend.calls == [("get", 42)]


def test_get_not_found_returns_safe_404() -> None:
    backend = FakePromptLibraryBackend()
    backend.error = PromptLibraryNotFoundError("secret upstream identifier")
    install_fake_backend(backend)

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/prompts/library/404"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Prompt library item was not found."}
    assert "secret" not in response.text
    assert backend.calls == [("get", 404)]


def test_get_non_integer_prompt_id_returns_standard_422() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get("/api/prompts/library/not-an-id")

    assert response.status_code == 422
    assert backend.calls == []


def test_search_uses_static_route_and_preserves_query_semantics() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get(
        "/api/prompts/library/search",
        params={"q": " REST API "},
    )

    assert response.status_code == 200
    assert response.json() == [item.model_dump(mode="json") for item in backend.items]
    assert backend.calls == [("search", PromptLibrarySearchRequest(q=" REST API "))]


@pytest.mark.parametrize(
    "url", ("/api/prompts/library/search", "/api/prompts/library/search?q=")
)
def test_search_missing_or_empty_query_returns_standard_422(url: str) -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get(url)

    assert response.status_code == 422
    assert backend.calls == []


def test_search_blank_query_returns_safe_422_without_backend_call() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).get(
        "/api/prompts/library/search",
        params={"q": "   "},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Prompt library input is invalid."}
    assert backend.calls == []


def _captured_update(
    backend: FakePromptLibraryBackend,
) -> tuple[int, PromptLibraryUpdateRequest]:
    assert len(backend.calls) == 1
    operation, captured = backend.calls[0]
    assert operation == "update"
    assert isinstance(captured, tuple)
    prompt_id, request = captured
    assert isinstance(prompt_id, int)
    assert isinstance(request, PromptLibraryUpdateRequest)
    return prompt_id, request


def test_update_omitted_wiki_rules_remain_omitted_at_backend_boundary() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).put(
        "/api/prompts/library/7",
        json={"title": "Updated title"},
    )

    prompt_id, request = _captured_update(backend)
    assert response.status_code == 200
    assert prompt_id == 7
    assert request.wiki_rules is None
    assert "wiki_rules" not in request.model_fields_set
    assert request.model_dump(exclude_unset=True, exclude_none=True) == {
        "title": "Updated title"
    }


def test_update_explicit_empty_wiki_rules_reach_backend_as_empty() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).put(
        "/api/prompts/library/7",
        json={"wiki_rules": []},
    )

    _, request = _captured_update(backend)
    assert response.status_code == 200
    assert request.wiki_rules == []
    assert "wiki_rules" in request.model_fields_set
    assert request.model_dump(exclude_unset=True, exclude_none=True) == {
        "wiki_rules": []
    }


def test_update_non_empty_wiki_rules_preserve_order() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).put(
        "/api/prompts/library/7",
        json={"wiki_rules": ["rule-a", "rule-b"]},
    )

    _, request = _captured_update(backend)
    assert response.status_code == 200
    assert request.wiki_rules == ["rule-a", "rule-b"]


def test_delete_returns_empty_204_and_calls_backend_once() -> None:
    backend = FakePromptLibraryBackend()
    install_fake_backend(backend)

    response = TestClient(app).delete("/api/prompts/library/9")

    assert response.status_code == 204
    assert response.content == b""
    assert backend.calls == [("delete", 9)]


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    (
        (
            InvalidPromptLibraryInputError("secret validation"),
            422,
            "Prompt library input is invalid.",
        ),
        (
            PromptLibraryNotFoundError("secret missing"),
            404,
            "Prompt library item was not found.",
        ),
        (
            PromptLibraryUpstreamError("secret upstream"),
            502,
            "Prompt library service is unavailable.",
        ),
        (
            PromptLibraryInternalError("secret internal"),
            500,
            "Prompt library operation failed during internal processing.",
        ),
        (
            RuntimeError("secret unexpected"),
            500,
            "Prompt library operation failed during internal processing.",
        ),
    ),
)
def test_library_errors_map_to_safe_stable_http_responses(
    error: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    backend = FakePromptLibraryBackend()
    backend.error = error
    install_fake_backend(backend)

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/prompts/library"
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert backend.calls == [("list", None)]


def test_upstream_error_does_not_leak_transport_or_persistence_details() -> None:
    backend = FakePromptLibraryBackend()
    backend.error = PromptLibraryUpstreamError(
        "http://secret-host:9999 password=secret DATABASE_URL traceback SQL"
    )
    install_fake_backend(backend)

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/prompts/library"
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Prompt library service is unavailable."}
    assert all(
        secret not in response.text
        for secret in (
            "secret-host",
            "password",
            "DATABASE_URL",
            "traceback",
            "SQL",
        )
    )


def test_production_dependency_uses_config_and_closes_request_client_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeLifecycleClient(FakePromptLibraryBackend):
        def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
            super().__init__()
            captured["base_url"] = base_url
            captured["timeout_seconds"] = timeout_seconds
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    monkeypatch.setattr(dependencies, "PromptVaultHttpClient", FakeLifecycleClient)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            prompt_vault_base_url="https://vault.example/api/",
            prompt_vault_timeout_seconds=17.5,
        ),
    )

    with contextmanager(dependencies.get_prompt_library_backend)() as backend:
        assert isinstance(backend, FakeLifecycleClient)
        assert backend.close_calls == 0

    assert captured == {
        "base_url": "https://vault.example/api",
        "timeout_seconds": 17.5,
    }
    assert backend.close_calls == 1


def test_library_routes_and_workbench_schemas_are_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert set(paths["/api/prompts/library"]) >= {"get", "post"}
    assert set(paths["/api/prompts/library/search"]) >= {"get"}
    assert set(paths["/api/prompts/library/{prompt_id}"]) >= {
        "get",
        "put",
        "delete",
    }
    assert "/api/prompts/experiment" in paths
    assert paths["/api/prompts/library"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/PromptLibraryItem"}
    assert (
        paths["/api/prompts/library/{prompt_id}"]["delete"]["responses"]["204"][
            "description"
        ]
        == "Successful Response"
    )

    components = schema["components"]["schemas"]
    assert {
        "PromptLibraryCreateRequest",
        "PromptLibraryItem",
        "PromptLibraryUpdateRequest",
    } <= set(components)
    for component_name in (
        "PromptLibraryCreateRequest",
        "PromptLibraryItem",
        "PromptLibraryUpdateRequest",
    ):
        wiki_rules = components[component_name]["properties"]["wiki_rules"]
        array_schema = wiki_rules.get("anyOf", [wiki_rules])[0]
        assert array_schema["type"] == "array"
        assert array_schema["items"] == {"type": "string"}


def test_prompt_library_route_uses_protocol_without_direct_http_details() -> None:
    source = inspect.getsource(prompt_api)

    assert "PromptLibraryBackend" in source
    assert "PromptVaultHttpClient" not in source
    assert "httpx" not in source
    assert "PROMPT_VAULT_BASE_URL" not in source
    assert "localhost" not in source


@pytest.mark.parametrize("method", ("PUT", "DELETE"))
def test_cors_allows_prompt_library_mutation_methods(method: str) -> None:
    response = TestClient(app).options(
        "/api/prompts/library/1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": method,
        },
    )

    assert response.status_code == 200
    assert method in response.headers["access-control-allow-methods"]
