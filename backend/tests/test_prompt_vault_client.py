import json
from collections.abc import Callable, Iterator

import httpx
import pytest

from agent_engineering_workbench.prompt_library_contracts import (
    PromptLibraryBackend,
    PromptLibraryCreateRequest,
    PromptLibraryItem,
    PromptLibrarySearchRequest,
    PromptLibraryUpdateRequest,
)
from agent_engineering_workbench.prompt_library_errors import (
    InvalidPromptLibraryInputError,
    PromptLibraryInternalError,
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
)
from agent_engineering_workbench.prompt_vault_client import PromptVaultHttpClient

type RequestHandler = Callable[[httpx.Request], httpx.Response]
type ClientFactory = Callable[[RequestHandler], PromptVaultHttpClient]


def prompt_payload(
    *,
    prompt_id: int = 1,
    wiki_rules: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": prompt_id,
        "title": "Research Assistant",
        "content": "You are a careful research assistant.",
        "wiki_rules": wiki_rules
        if wiki_rules is not None
        else ["Cite evidence.", "Do not infer unsupported claims."],
        "tags": tags if tags is not None else ["research", "grounded"],
        "created_at": "2026-08-30T01:00:00Z",
        "updated_at": "2026-08-30T02:00:00Z",
    }


def request_json(request: httpx.Request) -> dict[str, object]:
    decoded = json.loads(request.content)
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture
def client_factory() -> Iterator[ClientFactory]:
    clients: list[httpx.Client] = []

    def factory(handler: RequestHandler) -> PromptVaultHttpClient:
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(http_client)
        return PromptVaultHttpClient(
            base_url="http://vault.test/",
            timeout_seconds=3.0,
            http_client=http_client,
        )

    yield factory

    for client in clients:
        client.close()


def test_create_uses_exact_path_payload_status_and_response_contract(
    client_factory: ClientFactory,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json=prompt_payload())

    client = client_factory(handler)
    result = client.create_prompt(
        PromptLibraryCreateRequest(
            title="Research Assistant",
            content="You are a careful research assistant.",
            wiki_rules=["Cite evidence.", "Do not infer unsupported claims."],
            tags=["research", "grounded"],
        )
    )

    assert isinstance(result, PromptLibraryItem)
    assert len(captured) == 1
    assert captured[0].method == "POST"
    assert captured[0].url == "http://vault.test/prompts"
    assert "authorization" not in captured[0].headers
    assert request_json(captured[0]) == {
        "title": "Research Assistant",
        "content": "You are a careful research assistant.",
        "wiki_rules": ["Cite evidence.", "Do not infer unsupported claims."],
        "tags": ["research", "grounded"],
    }
    assert result.wiki_rules == [
        "Cite evidence.",
        "Do not infer unsupported claims.",
    ]
    assert result.tags == ["research", "grounded"]
    assert "created_at" not in result.model_dump()
    assert "updated_at" not in result.model_dump()


def test_list_preserves_upstream_order(client_factory: ClientFactory) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://vault.test/prompts"
        return httpx.Response(
            200,
            json=[prompt_payload(prompt_id=2), prompt_payload(prompt_id=1)],
        )

    results = client_factory(handler).list_prompts()

    assert [prompt.id for prompt in results] == [2, 1]


def test_get_uses_integer_prompt_id_path(client_factory: ClientFactory) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://vault.test/prompts/42"
        return httpx.Response(200, json=prompt_payload(prompt_id=42))

    result = client_factory(handler).get_prompt(42)

    assert result.id == 42


def test_search_uses_query_params_without_manual_encoding(
    client_factory: ClientFactory,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/prompts/search"
        assert request.url.params["q"] == "REST API + SQL"
        return httpx.Response(200, json=[prompt_payload()])

    results = client_factory(handler).search_prompts(
        PromptLibrarySearchRequest(q="REST API + SQL")
    )

    assert len(results) == 1


def test_update_omits_unset_wiki_rules_from_actual_json(
    client_factory: ClientFactory,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request_json(request)
        assert request.method == "PUT"
        assert request.url == "http://vault.test/prompts/1"
        assert payload == {"title": "Updated title"}
        assert "wiki_rules" not in payload
        return httpx.Response(200, json=prompt_payload())

    client_factory(handler).update_prompt(
        1,
        PromptLibraryUpdateRequest(title="Updated title"),
    )


def test_update_sends_explicit_empty_wiki_rules(
    client_factory: ClientFactory,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request_json(request)
        assert payload["wiki_rules"] == []
        return httpx.Response(200, json=prompt_payload(wiki_rules=[]))

    result = client_factory(handler).update_prompt(
        1,
        PromptLibraryUpdateRequest(wiki_rules=[]),
    )

    assert result.wiki_rules == []


def test_update_preserves_non_empty_wiki_rule_order(
    client_factory: ClientFactory,
) -> None:
    rules = ["Second stays second.", "First stays first."]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request_json(request)["wiki_rules"] == rules
        return httpx.Response(200, json=prompt_payload(wiki_rules=rules))

    result = client_factory(handler).update_prompt(
        1,
        PromptLibraryUpdateRequest(wiki_rules=rules),
    )

    assert result.wiki_rules == rules


def test_delete_accepts_only_204_and_does_not_parse_body(
    client_factory: ClientFactory,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url == "http://vault.test/prompts/7"
        return httpx.Response(204, content=b"not-json")

    client_factory(handler).delete_prompt(7)


def error_response(status: int, code: str) -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "error": {
                "code": code,
                "message": "A safe upstream message",
                "details": [],
            }
        },
    )


@pytest.mark.parametrize(
    ("status", "code", "expected_error"),
    (
        (422, "validation_error", InvalidPromptLibraryInputError),
        (404, "prompt_not_found", PromptLibraryNotFoundError),
        (500, "persistence_error", PromptLibraryUpstreamError),
        (500, "internal_error", PromptLibraryUpstreamError),
        (500, "future_error", PromptLibraryUpstreamError),
    ),
)
def test_stable_and_unknown_error_codes_map_to_workbench_boundary(
    client_factory: ClientFactory,
    status: int,
    code: str,
    expected_error: type[Exception],
) -> None:
    client = client_factory(lambda _request: error_response(status, code))

    with pytest.raises(expected_error) as captured:
        client.get_prompt(1)

    assert "A safe upstream message" not in str(captured.value)


@pytest.mark.parametrize("operation", ("get", "update", "delete"))
def test_item_operations_map_stable_404_to_not_found(
    client_factory: ClientFactory,
    operation: str,
) -> None:
    client = client_factory(lambda _request: error_response(404, "prompt_not_found"))

    with pytest.raises(PromptLibraryNotFoundError):
        if operation == "get":
            client.get_prompt(9)
        elif operation == "update":
            client.update_prompt(
                9,
                PromptLibraryUpdateRequest(title="Updated"),
            )
        else:
            client.delete_prompt(9)


@pytest.mark.parametrize(
    "response",
    (
        httpx.Response(500, content=b"not-json"),
        httpx.Response(500, json={}),
        httpx.Response(500, json={"error": {}}),
        httpx.Response(500, json={"error": {"code": "internal_error"}}),
        httpx.Response(
            500,
            json={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": {},
                }
            },
        ),
        httpx.Response(500, json={"error": "invalid"}),
    ),
)
def test_malformed_error_envelope_maps_to_upstream(
    client_factory: ClientFactory,
    response: httpx.Response,
) -> None:
    client = client_factory(lambda _request: response)

    with pytest.raises(PromptLibraryUpstreamError):
        client.get_prompt(1)


@pytest.mark.parametrize(
    "transport_error",
    (
        httpx.ConnectError("connection refused secret.internal"),
        httpx.ReadTimeout("timed out secret.internal"),
    ),
)
def test_transport_failures_map_to_safe_upstream_error(
    client_factory: ClientFactory,
    transport_error: httpx.HTTPError,
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        transport_error.request = request
        raise transport_error

    client = client_factory(handler)

    with pytest.raises(PromptLibraryUpstreamError) as captured:
        client.list_prompts()

    assert "secret.internal" not in str(captured.value)
    assert attempts == 1


@pytest.mark.parametrize(
    "response",
    (
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"id": 1}),
        httpx.Response(200, json={**prompt_payload(), "wiki_rules": "wrong"}),
    ),
)
def test_invalid_success_payload_maps_to_upstream(
    client_factory: ClientFactory,
    response: httpx.Response,
) -> None:
    client = client_factory(lambda _request: response)

    with pytest.raises(PromptLibraryUpstreamError):
        client.get_prompt(1)


def test_create_rejects_unexpected_200_status_even_with_valid_payload(
    client_factory: ClientFactory,
) -> None:
    client = client_factory(lambda _request: httpx.Response(200, json=prompt_payload()))

    with pytest.raises(PromptLibraryUpstreamError):
        client.create_prompt(
            PromptLibraryCreateRequest(title="Title", content="Content")
        )


def test_delete_rejects_unexpected_200_status(
    client_factory: ClientFactory,
) -> None:
    client = client_factory(lambda _request: httpx.Response(200, json={}))

    with pytest.raises(PromptLibraryUpstreamError):
        client.delete_prompt(1)


def test_injected_http_client_is_not_owned_and_close_is_idempotent() -> None:
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=[]))
    )
    client = PromptVaultHttpClient(
        base_url="http://vault.test",
        timeout_seconds=3.0,
        http_client=http_client,
    )

    client.close()
    client.close()

    assert http_client.is_closed is False
    http_client.close()


def test_explicitly_owned_http_client_is_closed_once_safely() -> None:
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=[]))
    )
    client = PromptVaultHttpClient(
        base_url="http://vault.test",
        timeout_seconds=3.0,
        http_client=http_client,
        owns_http_client=True,
    )

    client.close()
    client.close()

    assert http_client.is_closed is True


def test_closed_client_fails_before_transport_execution() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = PromptVaultHttpClient(
        base_url="http://vault.test",
        timeout_seconds=3.0,
        http_client=http_client,
    )
    client.close()

    with pytest.raises(PromptLibraryInternalError):
        client.list_prompts()

    assert requests == []
    http_client.close()


def test_client_satisfies_prompt_library_backend_protocol() -> None:
    def accepts_backend(backend: PromptLibraryBackend) -> PromptLibraryBackend:
        return backend

    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=[]))
    )
    client = PromptVaultHttpClient(
        base_url="http://vault.test",
        timeout_seconds=3.0,
        http_client=http_client,
    )

    assert accepts_backend(client) is client
    http_client.close()
