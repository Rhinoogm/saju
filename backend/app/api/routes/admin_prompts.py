from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.config import Settings, get_settings
from app.services.prompt_builder import FINAL_SYSTEM_PROMPT, FINAL_USER_PROMPT_TEMPLATE, QUESTION_SYSTEM_PROMPT, QUESTION_USER_PROMPT_TEMPLATE
from app.services.prompt_store import PromptRecord, PromptStore
from app.services.runtime_settings import resolve_runtime_llm_settings, save_runtime_llm_settings

router = APIRouter(prefix="/api/admin/prompts", tags=["admin"])
settings_router = APIRouter(prefix="/api/admin/settings", tags=["admin"])

DEFAULT_PROMPTS: dict[str, str] = {
    "question_system_prompt": QUESTION_SYSTEM_PROMPT,
    "question_user_prompt": QUESTION_USER_PROMPT_TEMPLATE,
    "final_system_prompt": FINAL_SYSTEM_PROMPT,
    "final_user_prompt": FINAL_USER_PROMPT_TEMPLATE,
}


class PromptUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class PromptResponse(BaseModel):
    name: str
    content: str
    updated_at: str

    @staticmethod
    def from_record(record: PromptRecord) -> "PromptResponse":
        return PromptResponse(name=record.name, content=record.content, updated_at=record.updated_at)


class LLMSettingsUpdateRequest(BaseModel):
    llm_provider: Literal["ollama", "groq"]
    groq_model: str = Field(min_length=1, max_length=200)
    ollama_model: str = Field(min_length=1, max_length=200)

    @field_validator("groq_model", "ollama_model", mode="before")
    @classmethod
    def strip_model_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class LLMSettingsResponse(BaseModel):
    llm_provider: Literal["ollama", "groq"]
    groq_model: str
    ollama_model: str
    updated_at: dict[str, str]


def require_admin(
    settings: Settings = Depends(get_settings),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API disabled")
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_prompt_store(request: Request) -> PromptStore:
    store = getattr(request.app.state, "prompt_store", None)
    if store is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prompt store not initialized")
    return store


@router.get("", response_model=list[PromptResponse], dependencies=[Depends(require_admin)])
async def list_prompts(store: PromptStore = Depends(get_prompt_store)) -> list[PromptResponse]:
    records = {record.name: record for record in store.list_prompts()}
    merged: list[PromptResponse] = []
    for name, default_content in DEFAULT_PROMPTS.items():
        record = records.get(name)
        if record is None:
            merged.append(PromptResponse(name=name, content=default_content, updated_at=""))
        else:
            merged.append(PromptResponse.from_record(record))
    return merged


@router.get("/{name}", response_model=PromptResponse, dependencies=[Depends(require_admin)])
async def get_prompt(name: str, store: PromptStore = Depends(get_prompt_store)) -> PromptResponse:
    record = store.get_prompt(name)
    if record is None:
        default = DEFAULT_PROMPTS.get(name)
        if default is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        return PromptResponse(name=name, content=default, updated_at="")
    return PromptResponse.from_record(record)


@router.put("/{name}", response_model=PromptResponse, dependencies=[Depends(require_admin)])
async def put_prompt(name: str, payload: PromptUpdateRequest, store: PromptStore = Depends(get_prompt_store)) -> PromptResponse:
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt content cannot be empty")
    record = store.set_prompt(name, content)
    return PromptResponse.from_record(record)


@settings_router.get("/llm", response_model=LLMSettingsResponse, dependencies=[Depends(require_admin)])
async def get_llm_settings(
    settings: Settings = Depends(get_settings),
    store: PromptStore = Depends(get_prompt_store),
) -> LLMSettingsResponse:
    runtime_settings = resolve_runtime_llm_settings(settings, store)
    return LLMSettingsResponse(
        llm_provider=runtime_settings.llm_provider,
        groq_model=runtime_settings.groq_model,
        ollama_model=runtime_settings.ollama_model,
        updated_at=runtime_settings.updated_at,
    )


@settings_router.put("/llm", response_model=LLMSettingsResponse, dependencies=[Depends(require_admin)])
async def put_llm_settings(
    payload: LLMSettingsUpdateRequest,
    store: PromptStore = Depends(get_prompt_store),
) -> LLMSettingsResponse:
    updated_at = save_runtime_llm_settings(
        store,
        llm_provider=payload.llm_provider,
        groq_model=payload.groq_model,
        ollama_model=payload.ollama_model,
    )
    return LLMSettingsResponse(
        llm_provider=payload.llm_provider,
        groq_model=payload.groq_model,
        ollama_model=payload.ollama_model,
        updated_at=updated_at,
    )
