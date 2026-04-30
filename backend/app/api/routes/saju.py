from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, Response, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.saju import (
    FinalReadingOutput,
    FinalReadingRequest,
    FinalReadingResponse,
    GenerateCustomQuestionsRequest,
    GenerateCustomQuestionsResponse,
    GenerateQuestionsResponse,
    QuestionGenerationOutput,
    ResponseMeta,
)
from app.services.calendar_service import CalendarCalculationError, CalendarService
from app.services.llm.base import (
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMServiceUnavailableError,
    LLMTimeoutError,
)
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.prompt_builder import build_custom_question_generation_prompt, build_final_reading_prompt
from app.services.prompt_store import PromptStore
from app.services.runtime_settings import resolve_runtime_llm_settings

logger = logging.getLogger(__name__)

ProviderCacheKey = tuple[Any, ...]


class LLMInvalidOutputError(ValueError):
    def __init__(self, *, label: str, content: str, reason: str, details: list[str] | None = None) -> None:
        super().__init__(f"LLM returned invalid {label}: {reason}")
        self.label = label
        self.content = content
        self.reason = reason
        self.details = details or []


def get_calendar_service() -> CalendarService:
    return CalendarService()


def get_prompt_store(request: Request) -> PromptStore | None:
    return getattr(request.app.state, "prompt_store", None)


def _shared_llm_http_client(request: Request) -> httpx.AsyncClient:
    client = getattr(request.app.state, "llm_http_client", None)
    if not isinstance(client, httpx.AsyncClient) or client.is_closed:
        client = httpx.AsyncClient()
        request.app.state.llm_http_client = client
        request.app.state.llm_provider_cache = {}
    return client


def _llm_provider_cache(request: Request) -> dict[ProviderCacheKey, LLMProvider]:
    cache = getattr(request.app.state, "llm_provider_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        request.app.state.llm_provider_cache = cache
    return cache


def _provider_cache_key(settings: Settings, runtime_provider: str, runtime_model: str) -> ProviderCacheKey:
    if runtime_provider == "groq":
        return (
            "groq",
            settings.groq_base_url,
            runtime_model,
            settings.groq_timeout_seconds,
            settings.groq_temperature,
            settings.groq_response_format_mode,
            settings.groq_json_schema_strict,
            settings.groq_max_completion_tokens,
            settings.groq_max_request_tokens,
        )
    if runtime_provider == "gemini":
        return (
            "gemini",
            settings.gemini_base_url,
            runtime_model,
            settings.gemini_timeout_seconds,
            settings.gemini_temperature,
            settings.gemini_response_schema_mode,
            settings.gemini_max_output_tokens,
        )
    return (
        "ollama",
        settings.ollama_base_url,
        runtime_model,
        settings.ollama_timeout_seconds,
        settings.ollama_temperature,
        settings.ollama_format_mode,
        settings.ollama_num_predict,
    )


def get_llm_provider(request: Request, settings: Settings = Depends(get_settings)) -> LLMProvider:
    runtime_settings = resolve_runtime_llm_settings(settings, get_prompt_store(request))
    runtime_model = {
        "groq": runtime_settings.groq_model,
        "gemini": runtime_settings.gemini_model,
        "ollama": runtime_settings.ollama_model,
    }[runtime_settings.llm_provider]
    http_client = _shared_llm_http_client(request)
    cache_key = _provider_cache_key(settings, runtime_settings.llm_provider, runtime_model)
    cache = _llm_provider_cache(request)
    cached_provider = cache.get(cache_key)
    if cached_provider is not None:
        request.state.llm_provider_cache = "hit"
        return cached_provider

    if runtime_settings.llm_provider == "groq":
        provider: LLMProvider = GroqProvider(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=runtime_settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
            temperature=settings.groq_temperature,
            response_format_mode=settings.groq_response_format_mode,
            json_schema_strict=settings.groq_json_schema_strict,
            max_completion_tokens=settings.groq_max_completion_tokens,
            max_request_tokens=settings.groq_max_request_tokens,
            client=http_client,
        )
        cache[cache_key] = provider
        request.state.llm_provider_cache = "miss"
        return provider

    if runtime_settings.llm_provider == "gemini":
        provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=runtime_settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
            temperature=settings.gemini_temperature,
            response_schema_mode=settings.gemini_response_schema_mode,
            max_output_tokens=settings.gemini_max_output_tokens,
            client=http_client,
        )
        cache[cache_key] = provider
        request.state.llm_provider_cache = "miss"
        return provider

    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=runtime_settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        temperature=settings.ollama_temperature,
        format_mode=settings.ollama_format_mode,
        num_predict=settings.ollama_num_predict,
        client=http_client,
    )
    cache[cache_key] = provider
    request.state.llm_provider_cache = "miss"
    return provider


def _numeric_usage_value(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _copy_usage_value(source: dict[str, Any], target: dict[str, int | float], source_key: str, target_key: str) -> None:
    value = _numeric_usage_value(source.get(source_key))
    if value is not None:
        target[target_key] = value


def _first_choice(raw_metadata: dict[str, Any]) -> dict[str, Any] | None:
    choices = raw_metadata.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0]
    return None


def _first_candidate(raw_metadata: dict[str, Any]) -> dict[str, Any] | None:
    candidates = raw_metadata.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        return candidates[0]
    return None


def _slim_raw_metadata(response: LLMResponse) -> dict[str, Any]:
    raw_metadata = response.raw_metadata
    if not isinstance(raw_metadata, dict):
        return {}

    usage: dict[str, int | float] = {}
    finish_reason: str | None = None

    if response.provider == "groq":
        raw_usage = raw_metadata.get("usage")
        if isinstance(raw_usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                _copy_usage_value(raw_usage, usage, key, key)
        choice = _first_choice(raw_metadata)
        if choice is not None and isinstance(choice.get("finish_reason"), str):
            finish_reason = choice["finish_reason"]
    elif response.provider == "gemini":
        raw_usage = raw_metadata.get("usageMetadata")
        if isinstance(raw_usage, dict):
            _copy_usage_value(raw_usage, usage, "promptTokenCount", "prompt_tokens")
            _copy_usage_value(raw_usage, usage, "candidatesTokenCount", "completion_tokens")
            _copy_usage_value(raw_usage, usage, "totalTokenCount", "total_tokens")
        candidate = _first_candidate(raw_metadata)
        if candidate is not None and isinstance(candidate.get("finishReason"), str):
            finish_reason = candidate["finishReason"]
    elif response.provider == "ollama":
        _copy_usage_value(raw_metadata, usage, "prompt_eval_count", "prompt_tokens")
        _copy_usage_value(raw_metadata, usage, "eval_count", "completion_tokens")
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
            usage["total_tokens"] = prompt_tokens + completion_tokens
        if isinstance(raw_metadata.get("done_reason"), str):
            finish_reason = raw_metadata["done_reason"]

    slimmed: dict[str, Any] = {}
    if usage:
        slimmed["usage"] = usage
    if finish_reason:
        slimmed["finish_reason"] = finish_reason
    return slimmed


def _meta(response: LLMResponse) -> ResponseMeta:
    return ResponseMeta(
        provider=response.provider,
        model=response.model,
        raw_metadata=_slim_raw_metadata(response),
    )


def _estimate_text_tokens(value: str) -> int:
    if not value:
        return 0
    return max((len(value) + 3) // 4, (len(value.encode("utf-8")) + 2) // 3)


def _usage_metric(response: LLMResponse, key: str) -> int | float | None:
    slim_metadata = _slim_raw_metadata(response)
    usage = slim_metadata.get("usage")
    if not isinstance(usage, dict):
        return None
    return _numeric_usage_value(usage.get(key))


def _set_llm_debug_headers(
    *,
    request: Request,
    http_response: Response,
    settings: Settings,
    llm_response: LLMResponse,
    schema_name: str,
    system: str,
    prompt: str,
    schema: dict,
    duration_ms: float,
    max_output_tokens: int | None,
) -> None:
    if not settings.llm_debug_metrics_enabled:
        return

    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    prompt_chars = len(system) + len(prompt) + len(schema_json)
    estimated_prompt_tokens = (
        _estimate_text_tokens(system)
        + _estimate_text_tokens(prompt)
        + _estimate_text_tokens(schema_json)
    )
    provider_cache = getattr(request.state, "llm_provider_cache", "unknown")
    prompt_tokens = _usage_metric(llm_response, "prompt_tokens")
    completion_tokens = _usage_metric(llm_response, "completion_tokens")
    total_tokens = _usage_metric(llm_response, "total_tokens")

    headers: dict[str, str] = {
        "X-LLM-Duration-Ms": f"{duration_ms:.2f}",
        "X-LLM-Prompt-Chars": str(prompt_chars),
        "X-LLM-Estimated-Prompt-Tokens": str(estimated_prompt_tokens),
        "X-LLM-Provider-Cache": str(provider_cache),
        "Server-Timing": f"llm;dur={duration_ms:.2f}",
    }
    if prompt_tokens is not None:
        headers["X-LLM-Prompt-Tokens"] = str(prompt_tokens)
    if completion_tokens is not None:
        headers["X-LLM-Completion-Tokens"] = str(completion_tokens)
    if total_tokens is not None:
        headers["X-LLM-Total-Tokens"] = str(total_tokens)
    if max_output_tokens is not None:
        headers["X-LLM-Max-Output-Tokens"] = str(max_output_tokens)

    for header, value in headers.items():
        http_response.headers[header] = value

    logger.info(
        "LLM debug metrics schema=%s provider=%s model=%s duration_ms=%.2f prompt_chars=%s "
        "estimated_prompt_tokens=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s "
        "max_output_tokens=%s provider_cache=%s",
        schema_name,
        llm_response.provider,
        llm_response.model,
        duration_ms,
        prompt_chars,
        estimated_prompt_tokens,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        max_output_tokens,
        provider_cache,
    )


async def _call_llm(
    llm_provider: LLMProvider,
    *,
    request: Request,
    http_response: Response,
    settings: Settings,
    system: str,
    prompt: str,
    schema: dict,
    schema_name: str,
    max_output_tokens: int | None,
) -> LLMResponse:
    started_at = time.perf_counter()
    try:
        llm_response = await llm_provider.generate(
            system=system,
            prompt=prompt,
            schema=schema,
            schema_name=schema_name,
            max_output_tokens=max_output_tokens,
        )
        _set_llm_debug_headers(
            request=request,
            http_response=http_response,
            settings=settings,
            llm_response=llm_response,
            schema_name=schema_name,
            system=system,
            prompt=prompt,
            schema=schema,
            duration_ms=(time.perf_counter() - started_at) * 1000,
            max_output_tokens=max_output_tokens,
        )
        return llm_response
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except LLMRateLimitError as exc:
        logger.warning("LLM rate limit while generating %s: %s", schema_name, exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc) or "무료 모델 사용 한도에 도달했어요. 잠시 뒤 다시 시도해주세요.",
        ) from exc
    except LLMServiceUnavailableError as exc:
        logger.warning("LLM provider unavailable while generating %s: %s", schema_name, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.exception("LLM provider failed while generating %s", schema_name)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _parse_questions(content: str) -> QuestionGenerationOutput:
    try:
        return QuestionGenerationOutput.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM returned invalid question JSON",
        ) from exc


def _parse_final_reading(content: str) -> FinalReadingOutput:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMInvalidOutputError(
            label="final reading JSON",
            content=content,
            reason=f"JSON syntax error at char {exc.pos}: {exc.msg}",
        ) from exc

    try:
        return FinalReadingOutput.model_validate(parsed)
    except ValidationError as exc:
        details = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            details.append(f"{location}: {error['msg']}")
        raise LLMInvalidOutputError(
            label="final reading schema",
            content=content,
            reason="schema validation failed",
            details=details,
        ) from exc


def _invalid_final_reading_http_error(error: LLMInvalidOutputError) -> HTTPException:
    details = "; ".join(error.details[:8]) if error.details else error.reason
    logger.warning(
        "Invalid final reading output from LLM. label=%s reason=%s details=%s",
        error.label,
        error.reason,
        details,
    )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"LLM returned invalid final reading output. Reason: {details}.",
    )
