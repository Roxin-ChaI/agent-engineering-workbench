from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ImmutablePromptLibraryContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _validate_wiki_rules(value: list[str]) -> list[str]:
    if any(not rule.strip() for rule in value):
        raise ValueError("wiki_rules must not contain blank values")
    return value


class PromptLibraryItem(_ImmutablePromptLibraryContract):
    id: int
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    wiki_rules: list[str]
    tags: list[str]

    @field_validator("wiki_rules")
    @classmethod
    def validate_wiki_rules(cls, value: list[str]) -> list[str]:
        return _validate_wiki_rules(value)


class PromptLibraryCreateRequest(_ImmutablePromptLibraryContract):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    wiki_rules: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("wiki_rules")
    @classmethod
    def validate_wiki_rules(cls, value: list[str]) -> list[str]:
        return _validate_wiki_rules(value)


class PromptLibraryUpdateRequest(_ImmutablePromptLibraryContract):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    wiki_rules: list[str] | None = None
    tags: list[str] | None = None

    @field_validator("wiki_rules")
    @classmethod
    def validate_wiki_rules(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None
        return _validate_wiki_rules(value)


class PromptLibrarySearchRequest(_ImmutablePromptLibraryContract):
    q: str = Field(min_length=1)

    @field_validator("q")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("q must not be blank")
        return value


type PromptLibraryList = list[PromptLibraryItem]


class PromptLibraryBackend(Protocol):
    def create_prompt(
        self,
        request: PromptLibraryCreateRequest,
    ) -> PromptLibraryItem: ...

    def list_prompts(self) -> PromptLibraryList: ...

    def get_prompt(self, prompt_id: int) -> PromptLibraryItem: ...

    def search_prompts(
        self,
        request: PromptLibrarySearchRequest,
    ) -> PromptLibraryList: ...

    def update_prompt(
        self,
        prompt_id: int,
        request: PromptLibraryUpdateRequest,
    ) -> PromptLibraryItem: ...

    def delete_prompt(self, prompt_id: int) -> None: ...
