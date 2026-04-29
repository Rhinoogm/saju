from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from urllib.parse import quote

import httpx

from app.services.llm.base import LLMProviderError, LLMRateLimitError, LLMResponse, LLMTimeoutError

_ERROR_BODY_LIMIT = 500
_DEFAULT_TRANSIENT_RETRY_SECONDS = 1.0
_MAX_TRANSIENT_RETRY_SECONDS = 10.0
_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})


class GeminiProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 60.0,
        temperature: float = 0.25,
        response_schema_mode: Literal["json_schema", "json", "none"] = "json_schema",
        max_output_tokens: int | None = 5000,
        transport: httpx.AsyncBaseTransport | None = None,
        max_transient_retries: int = 2,
        transient_retry_seconds: float = _DEFAULT_TRANSIENT_RETRY_SECONDS,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.response_schema_mode = response_schema_mode
        self.max_output_tokens = max_output_tokens
        self.transport = transport
        self.max_transient_retries = max(0, max_transient_retries)
        self.transient_retry_seconds = max(0.0, transient_retry_seconds)
        self.sleep = sleep or asyncio.sleep

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/models/{quote(self.model, safe='')}:generateContent"

    @staticmethod
    def _prompt_with_schema(prompt: str, *, schema: dict[str, Any], schema_name: str) -> str:
        schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        return (
            f"{prompt}\n\n"
            "반드시 아래 JSON Schema를 만족하는 JSON 객체만 반환하라.\n"
            f"Schema name: {schema_name}\n"
            f"JSON Schema: {schema_json}"
        )

    @classmethod
    def _schema_for_gemini(cls, schema: dict[str, Any]) -> dict[str, Any]:
        root = copy.deepcopy(schema)
        definitions = root.get("$defs")

        def resolve(value: Any) -> Any:
            if isinstance(value, list):
                return [resolve(item) for item in value]
            if not isinstance(value, dict):
                return value

            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/") and isinstance(definitions, dict):
                name = ref.removeprefix("#/$defs/")
                target = definitions.get(name)
                if isinstance(target, dict):
                    merged = {**copy.deepcopy(target), **{key: val for key, val in value.items() if key != "$ref"}}
                    return resolve(merged)

            nullable_schema = cls._nullable_union_schema(value)
            if nullable_schema is not None:
                return resolve(nullable_schema)

            result: dict[str, Any] = {}
            for key, item in value.items():
                if key in {"$defs", "$schema", "default"}:
                    continue
                if key == "properties" and isinstance(item, dict):
                    result[key] = {property_name: resolve(property_schema) for property_name, property_schema in item.items()}
                    result["propertyOrdering"] = list(item.keys())
                    continue
                result[key] = resolve(item)
            return result

        resolved = resolve(root)
        return resolved if isinstance(resolved, dict) else schema

    @staticmethod
    def _nullable_union_schema(schema: dict[str, Any]) -> dict[str, Any] | None:
        variants = schema.get("anyOf") or schema.get("oneOf")
        if not isinstance(variants, list) or len(variants) != 2:
            return None

        null_variants = [variant for variant in variants if isinstance(variant, dict) and variant.get("type") == "null"]
        non_null_variants = [variant for variant in variants if variant not in null_variants]
        if len(null_variants) != 1 or len(non_null_variants) != 1 or not isinstance(non_null_variants[0], dict):
            return None

        merged = {key: value for key, value in schema.items() if key not in {"anyOf", "oneOf"}}
        merged.update(non_null_variants[0])
        non_null_type = merged.get("type")
        if isinstance(non_null_type, str):
            merged["type"] = [non_null_type, "null"]
        return merged

    def _build_payload(self, *, system: str, prompt: str, schema: dict[str, Any], schema_name: str) -> dict[str, Any]:
        user_prompt = prompt
        generation_config: dict[str, Any] = {
            "temperature": self.temperature,
        }
        if self.max_output_tokens is not None:
            generation_config["maxOutputTokens"] = self.max_output_tokens

        if self.response_schema_mode == "json_schema":
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseJsonSchema"] = self._schema_for_gemini(schema)
        elif self.response_schema_mode == "json":
            generation_config["responseMimeType"] = "application/json"
            user_prompt = self._prompt_with_schema(prompt, schema=schema, schema_name=schema_name)
        else:
            user_prompt = self._prompt_with_schema(prompt, schema=schema, schema_name=schema_name)

        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

    @staticmethod
    def _response_error_text(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:_ERROR_BODY_LIMIT] or "<empty response body>"

        error = body.get("error") if isinstance(body, dict) else None
        if not isinstance(error, dict):
            return response.text[:_ERROR_BODY_LIMIT] or "<empty response body>"

        message = error.get("message")
        status = error.get("status")
        code = error.get("code")
        details = []
        if isinstance(status, str) and status:
            details.append(f"status={status}")
        if isinstance(code, int):
            details.append(f"code={code}")

        if isinstance(message, str) and message:
            if details:
                return f"{message} ({', '.join(details)})"[:_ERROR_BODY_LIMIT]
            return message[:_ERROR_BODY_LIMIT]

        return json.dumps(error, ensure_ascii=False, separators=(",", ":"))[:_ERROR_BODY_LIMIT]

    @staticmethod
    def _is_quota_or_rate_limit_response(status_code: int, error_text: str) -> bool:
        if status_code == 429:
            return True
        if status_code not in {400, 403}:
            return False
        normalized_error = error_text.lower()
        return any(
            marker in normalized_error
            for marker in (
                "quota",
                "rate limit",
                "resource_exhausted",
                "too many requests",
            )
        )

    @staticmethod
    def _is_transient_overload_response(status_code: int, error_text: str) -> bool:
        if status_code not in _TRANSIENT_STATUS_CODES:
            return False
        normalized_error = error_text.lower()
        return status_code == 503 or any(
            marker in normalized_error
            for marker in (
                "unavailable",
                "high demand",
                "overloaded",
                "temporarily",
                "try again later",
            )
        )

    @staticmethod
    def _retry_after_seconds(retry_after: str | None) -> float | None:
        if not retry_after:
            return None
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None

    @staticmethod
    def _transient_error_message(error_text: str) -> str:
        if "high demand" in error_text.lower() or "unavailable" in error_text.lower():
            return "Gemini 모델 사용량이 많아 응답하지 못했어요. 잠시 후 다시 시도해주세요."
        return "Gemini 모델이 일시적으로 응답하지 못했어요. 잠시 후 다시 시도해주세요."

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

        payload = self._build_payload(system=system, prompt=prompt, schema=schema, schema_name=schema_name)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        transient_retry_count = 0

        while True:
            try:
                client_options: dict[str, Any] = {"timeout": self.timeout_seconds}
                if self.transport is not None:
                    client_options["transport"] = self.transport

                async with httpx.AsyncClient(**client_options) as client:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
                    response.raise_for_status()
                break
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("Gemini request timed out") from exc
            except httpx.HTTPStatusError as exc:
                error_text = self._response_error_text(exc.response)
                if self._is_quota_or_rate_limit_response(exc.response.status_code, error_text):
                    raise LLMRateLimitError(f"Gemini API limit reached: {error_text}") from exc

                if self._is_transient_overload_response(exc.response.status_code, error_text):
                    retry_after = self._retry_after_seconds(exc.response.headers.get("Retry-After"))
                    retry_delay = retry_after if retry_after is not None else self.transient_retry_seconds
                    if transient_retry_count < self.max_transient_retries and retry_delay <= _MAX_TRANSIENT_RETRY_SECONDS:
                        transient_retry_count += 1
                        await self.sleep(retry_delay)
                        continue
                    raise LLMProviderError(self._transient_error_message(error_text)) from exc

                raise LLMProviderError(f"Gemini returned HTTP {exc.response.status_code}: {error_text}") from exc
            except httpx.HTTPError as exc:
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        body = response.json()
        try:
            candidate = body["candidates"][0]
            parts = candidate["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("Gemini response did not include candidates[0].content.parts") from exc

        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not content.strip():
            raise LLMProviderError("Gemini response content was empty")

        if isinstance(candidate, dict) and candidate.get("finishReason") == "MAX_TOKENS":
            limit_hint = (
                f"GEMINI_MAX_OUTPUT_TOKENS={self.max_output_tokens}"
                if self.max_output_tokens is not None
                else "the configured Gemini output token limit"
            )
            raise LLMProviderError(
                f"Gemini stopped before completing the response because {limit_hint} was reached. "
                "Increase GEMINI_MAX_OUTPUT_TOKENS or shorten the prompt."
            )

        return LLMResponse(content=content, model=body.get("modelVersion", self.model), provider="gemini", raw_metadata=body)
