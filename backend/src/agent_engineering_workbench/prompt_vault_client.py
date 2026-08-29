from http import HTTPStatus

import httpx
from pydantic import ValidationError

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
    PromptLibraryInternalError,
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
)

_PROMPT_ITEM_FIELDS = ("id", "title", "content", "wiki_rules", "tags")


class PromptVaultHttpClient(PromptLibraryBackend):
    """Translate Workbench prompt library contracts over Prompt Vault HTTP."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        http_client: httpx.Client | None = None,
        owns_http_client: bool = False,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise ValueError("base_url must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._base_url = normalized_base_url
        self._http_client = http_client or httpx.Client(
            timeout=timeout_seconds,
        )
        self._owns_http_client = http_client is None or owns_http_client
        self._closed = False

    def create_prompt(
        self,
        request: PromptLibraryCreateRequest,
    ) -> PromptLibraryItem:
        response = self._request(
            "POST",
            "/prompts",
            expected_status=HTTPStatus.CREATED,
            json=request.model_dump(mode="json"),
        )
        return self._parse_item(response)

    def list_prompts(self) -> PromptLibraryList:
        response = self._request(
            "GET",
            "/prompts",
            expected_status=HTTPStatus.OK,
        )
        return self._parse_items(response)

    def get_prompt(self, prompt_id: int) -> PromptLibraryItem:
        response = self._request(
            "GET",
            f"/prompts/{prompt_id}",
            expected_status=HTTPStatus.OK,
        )
        return self._parse_item(response)

    def search_prompts(
        self,
        request: PromptLibrarySearchRequest,
    ) -> PromptLibraryList:
        response = self._request(
            "GET",
            "/prompts/search",
            expected_status=HTTPStatus.OK,
            params={"q": request.q},
        )
        return self._parse_items(response)

    def update_prompt(
        self,
        prompt_id: int,
        request: PromptLibraryUpdateRequest,
    ) -> PromptLibraryItem:
        response = self._request(
            "PUT",
            f"/prompts/{prompt_id}",
            expected_status=HTTPStatus.OK,
            json=request.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_none=True,
            ),
        )
        return self._parse_item(response)

    def delete_prompt(self, prompt_id: int) -> None:
        self._request(
            "DELETE",
            f"/prompts/{prompt_id}",
            expected_status=HTTPStatus.NO_CONTENT,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if not self._owns_http_client:
            return

        try:
            self._http_client.close()
        except Exception as exc:
            raise PromptLibraryInternalError(
                "Prompt Vault client cleanup failed."
            ) from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected_status: HTTPStatus,
        json: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        if self._closed:
            raise PromptLibraryInternalError("Prompt Vault client is unavailable.")

        try:
            response = self._http_client.request(
                method,
                f"{self._base_url}{path}",
                json=json,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise PromptLibraryUpstreamError("Prompt Vault request failed.") from exc

        if response.status_code != expected_status:
            self._raise_response_error(response)
        return response

    @staticmethod
    def _parse_item(response: httpx.Response) -> PromptLibraryItem:
        try:
            return PromptVaultHttpClient._parse_item_payload(response.json())
        except (KeyError, ValidationError, ValueError, TypeError) as exc:
            raise PromptLibraryUpstreamError(
                "Prompt Vault returned an invalid response."
            ) from exc

    @staticmethod
    def _parse_items(response: httpx.Response) -> PromptLibraryList:
        try:
            payload = response.json()
            if not isinstance(payload, list):
                raise TypeError("Prompt Vault list response must be an array")
            return [PromptVaultHttpClient._parse_item_payload(item) for item in payload]
        except (KeyError, ValidationError, ValueError, TypeError) as exc:
            raise PromptLibraryUpstreamError(
                "Prompt Vault returned an invalid response."
            ) from exc

    @staticmethod
    def _parse_item_payload(payload: object) -> PromptLibraryItem:
        if not isinstance(payload, dict):
            raise TypeError("Prompt Vault item response must be an object")
        workbench_payload = {field: payload[field] for field in _PROMPT_ITEM_FIELDS}
        return PromptLibraryItem.model_validate(workbench_payload)

    @staticmethod
    def _raise_response_error(response: httpx.Response) -> None:
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Prompt Vault error response must be an object")
            error = payload["error"]
            if not isinstance(error, dict):
                raise TypeError("Prompt Vault error detail must be an object")
            code = error["code"]
            message = error["message"]
            details = error.get("details")
            if not isinstance(code, str) or not isinstance(message, str):
                raise TypeError("Prompt Vault error code and message must be strings")
            if details is not None and not isinstance(details, list):
                raise TypeError("Prompt Vault error details must be an array")
        except (KeyError, TypeError, ValueError):
            raise PromptLibraryUpstreamError(
                "Prompt Vault returned an invalid error response."
            ) from None

        if (
            response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
            and code == "validation_error"
        ):
            raise InvalidPromptLibraryInputError("Prompt library request is invalid.")
        if response.status_code == HTTPStatus.NOT_FOUND and code == "prompt_not_found":
            raise PromptLibraryNotFoundError("Prompt library item was not found.")
        raise PromptLibraryUpstreamError("Prompt Vault request failed.")
