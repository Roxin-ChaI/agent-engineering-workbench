import pytest
from pydantic import TypeAdapter, ValidationError

from agent_engineering_workbench.prompt_contracts import PromptExperimentRequest
from agent_engineering_workbench.prompt_library_contracts import (
    PromptLibraryBackend,
    PromptLibraryCreateRequest,
    PromptLibraryItem,
    PromptLibraryList,
    PromptLibrarySearchRequest,
    PromptLibraryUpdateRequest,
)
from agent_engineering_workbench.prompt_library_errors import (
    InvalidPromptLibraryInputError,
    PromptLibraryError,
    PromptLibraryInternalError,
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
)


def make_item() -> PromptLibraryItem:
    return PromptLibraryItem(
        id=1,
        title="Research Assistant",
        content="You are a careful research assistant.",
        wiki_rules=["Cite evidence.", "Do not infer unsupported claims."],
        tags=["research", "grounded"],
    )


def test_prompt_library_item_round_trip_preserves_complete_contract() -> None:
    item = make_item()

    assert PromptLibraryItem.model_validate_json(item.model_dump_json()) == item
    assert item.model_dump(mode="json") == {
        "id": 1,
        "title": "Research Assistant",
        "content": "You are a careful research assistant.",
        "wiki_rules": ["Cite evidence.", "Do not infer unsupported claims."],
        "tags": ["research", "grounded"],
    }


def test_prompt_library_item_preserves_ordered_wiki_rules_and_tags() -> None:
    item = make_item()

    assert item.wiki_rules == [
        "Cite evidence.",
        "Do not infer unsupported claims.",
    ]
    assert item.tags == ["research", "grounded"]


def test_prompt_library_item_allows_empty_wiki_rules_and_tags() -> None:
    item = make_item().model_copy(update={"wiki_rules": [], "tags": []})

    assert PromptLibraryItem.model_validate(item.model_dump()) == item


def test_create_request_uses_upstream_compatible_defaults() -> None:
    request = PromptLibraryCreateRequest(
        title="Summarizer",
        content="Summarize the supplied text.",
    )

    assert request.wiki_rules == []
    assert request.tags == []
    assert request.model_dump(mode="json") == {
        "title": "Summarizer",
        "content": "Summarize the supplied text.",
        "wiki_rules": [],
        "tags": [],
    }


def test_update_omitted_wiki_rules_remain_distinguishable() -> None:
    request = PromptLibraryUpdateRequest(title="Updated title")

    assert request.wiki_rules is None
    assert "wiki_rules" not in request.model_fields_set
    assert request.model_dump(exclude_unset=True, exclude_none=True) == {
        "title": "Updated title"
    }


def test_update_explicit_empty_wiki_rules_remain_distinguishable() -> None:
    request = PromptLibraryUpdateRequest(wiki_rules=[])

    assert request.wiki_rules == []
    assert "wiki_rules" in request.model_fields_set
    assert request.model_dump(exclude_unset=True, exclude_none=True) == {
        "wiki_rules": []
    }


def test_update_accepts_non_empty_partial_fields_without_reordering() -> None:
    request = PromptLibraryUpdateRequest(
        content="Use the updated instructions.",
        wiki_rules=["First", "Second"],
        tags=["Beta", "beta", "Beta"],
    )

    assert request.wiki_rules == ["First", "Second"]
    assert request.tags == ["Beta", "beta", "Beta"]
    assert request.model_dump(exclude_unset=True, exclude_none=True) == {
        "content": "Use the updated instructions.",
        "wiki_rules": ["First", "Second"],
        "tags": ["Beta", "beta", "Beta"],
    }


def test_prompt_library_list_is_a_direct_array_contract() -> None:
    payload = [make_item().model_dump(mode="json")]

    items: PromptLibraryList = TypeAdapter(PromptLibraryList).validate_python(payload)

    assert items == [make_item()]


def test_search_request_accepts_non_blank_substring_query() -> None:
    request = PromptLibrarySearchRequest(q=" REST API ")

    assert request.q == " REST API "


@pytest.mark.parametrize(
    ("contract", "payload"),
    (
        (PromptLibraryItem, {**make_item().model_dump(), "id": "one"}),
        (
            PromptLibraryCreateRequest,
            {"title": "", "content": "Valid content"},
        ),
        (
            PromptLibraryCreateRequest,
            {"title": "Valid", "content": ""},
        ),
        (
            PromptLibraryCreateRequest,
            {
                "title": "Valid",
                "content": "Valid",
                "wiki_rules": ["   "],
            },
        ),
        (PromptLibrarySearchRequest, {"q": "  "}),
    ),
)
def test_prompt_library_contracts_reject_invalid_basic_values(
    contract: type[PromptLibraryItem]
    | type[PromptLibraryCreateRequest]
    | type[PromptLibrarySearchRequest],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


def test_prompt_library_errors_form_one_workbench_owned_boundary() -> None:
    error_types = (
        InvalidPromptLibraryInputError,
        PromptLibraryNotFoundError,
        PromptLibraryUpstreamError,
        PromptLibraryInternalError,
    )

    assert all(issubclass(error_type, PromptLibraryError) for error_type in error_types)
    assert issubclass(InvalidPromptLibraryInputError, ValueError)


def test_prompt_library_backend_protocol_exposes_required_operations() -> None:
    expected_methods = {
        "create_prompt",
        "list_prompts",
        "get_prompt",
        "search_prompts",
        "update_prompt",
        "delete_prompt",
    }

    assert expected_methods <= set(PromptLibraryBackend.__dict__)


def test_prompt_experiment_contract_remains_isolated() -> None:
    schema = PromptExperimentRequest.model_json_schema()
    schema_text = str(schema)

    assert "PromptLibrary" not in schema_text
    assert "prompt_id" not in schema_text
