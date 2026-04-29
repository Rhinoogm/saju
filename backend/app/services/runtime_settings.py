from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from app.config import Settings
from app.services.prompt_store import PromptStore

LLM_PROVIDER_KEY = "llm_provider"
GROQ_MODEL_KEY = "groq_model"
OLLAMA_MODEL_KEY = "ollama_model"
GEMINI_MODEL_KEY = "gemini_model"

LLMProviderName = Literal["ollama", "groq", "gemini"]


@dataclass(frozen=True)
class RuntimeLLMSettings:
    llm_provider: LLMProviderName
    groq_model: str
    ollama_model: str
    gemini_model: str
    updated_at: dict[str, str]


def _setting_value(store: PromptStore | None, key: str, default: str) -> tuple[str, str]:
    if store is None:
        return default, ""
    record = store.get_setting(key)
    if record is None:
        return default, ""
    value = record.value.strip()
    return (value if value else default), record.updated_at


def resolve_runtime_llm_settings(settings: Settings, store: PromptStore | None) -> RuntimeLLMSettings:
    provider, provider_updated_at = _setting_value(store, LLM_PROVIDER_KEY, settings.llm_provider)
    if provider not in ("ollama", "groq", "gemini"):
        provider = settings.llm_provider
        provider_updated_at = ""
    runtime_provider = cast(LLMProviderName, provider)

    groq_model, groq_updated_at = _setting_value(store, GROQ_MODEL_KEY, settings.groq_model)
    ollama_model, ollama_updated_at = _setting_value(store, OLLAMA_MODEL_KEY, settings.ollama_model)
    gemini_model, gemini_updated_at = _setting_value(store, GEMINI_MODEL_KEY, settings.gemini_model)

    return RuntimeLLMSettings(
        llm_provider=runtime_provider,
        groq_model=groq_model,
        ollama_model=ollama_model,
        gemini_model=gemini_model,
        updated_at={
            LLM_PROVIDER_KEY: provider_updated_at,
            GROQ_MODEL_KEY: groq_updated_at,
            OLLAMA_MODEL_KEY: ollama_updated_at,
            GEMINI_MODEL_KEY: gemini_updated_at,
        },
    )


def save_runtime_llm_settings(
    store: PromptStore,
    *,
    llm_provider: LLMProviderName,
    groq_model: str,
    ollama_model: str,
    gemini_model: str,
) -> dict[str, str]:
    records = [
        store.set_setting(LLM_PROVIDER_KEY, llm_provider),
        store.set_setting(GROQ_MODEL_KEY, groq_model),
        store.set_setting(OLLAMA_MODEL_KEY, ollama_model),
        store.set_setting(GEMINI_MODEL_KEY, gemini_model),
    ]
    return {record.key: record.updated_at for record in records}
