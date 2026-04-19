from __future__ import annotations

import json
from typing import Any, Literal

import httpx

from app.services.llm.base import LLMProviderError, LLMRateLimitError, LLMResponse, LLMTimeoutError

_ERROR_BODY_LIMIT = 500
_TOKEN_BUDGET_BUFFER = 128
_MIN_COMPLETION_TOKENS = 256
_JSON_SCHEMA_RESPONSE_FORMAT = "json_schema"
_JSON_OBJECT_RESPONSE_FORMAT = "json_object"
_STRICT_JSON_SCHEMA_MODELS = frozenset(
    {
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    }
)
_BEST_EFFORT_JSON_SCHEMA_MODELS = _STRICT_JSON_SCHEMA_MODELS | frozenset(
    {
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "openai/gpt-oss-safeguard-20b",
    }
)
_DEFAULT_RESPONSE_FORMAT = object()


class GroqProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
        model: str = "llama-3.1-8b-instant",
        timeout_seconds: float = 60.0,
        temperature: float = 0.25,
        response_format_mode: Literal["auto", "json_schema", "json_object", "none"] = "auto",
        json_schema_strict: bool = True,
        max_completion_tokens: int | None = 4096,
        max_request_tokens: int | None = 8000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.response_format_mode = response_format_mode
        self.json_schema_strict = json_schema_strict
        self.max_completion_tokens = max_completion_tokens
        self.max_request_tokens = max_request_tokens
        self.transport = transport

    def _auto_json_schema_strict(self) -> bool | None:
        model = self.model.lower()
        if model in _STRICT_JSON_SCHEMA_MODELS:
            return True
        if model in _BEST_EFFORT_JSON_SCHEMA_MODELS:
            return False
        return None

    def _response_format(self, *, schema: dict[str, Any], schema_name: str) -> dict[str, Any] | None:
        if self.response_format_mode == "none":
            return None
        if self.response_format_mode == "json_object":
            return {"type": _JSON_OBJECT_RESPONSE_FORMAT}

        strict = self.json_schema_strict
        if self.response_format_mode == "auto":
            auto_strict = self._auto_json_schema_strict()
            if auto_strict is None:
                return {"type": _JSON_OBJECT_RESPONSE_FORMAT}
            strict = auto_strict

        return {
            "type": _JSON_SCHEMA_RESPONSE_FORMAT,
            "json_schema": {
                "name": schema_name,
                "schema": schema,
                "strict": strict,
            },
        }

    @staticmethod
    def _prompt_with_schema(prompt: str, *, schema: dict[str, Any], schema_name: str) -> str:
        schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        return (
            f"{prompt}\n\n"
            "반드시 아래 JSON Schema를 만족하는 JSON 객체만 반환하라.\n"
            f"Schema name: {schema_name}\n"
            f"JSON Schema: {schema_json}"
        )

    @staticmethod
    def _estimate_text_tokens(value: str) -> int:
        if not value:
            return 0
        return max((len(value) + 3) // 4, (len(value.encode("utf-8")) + 2) // 3)

    @classmethod
    def _estimate_payload_tokens(cls, payload: dict[str, Any]) -> int:
        payload_without_completion = {
            key: value
            for key, value in payload.items()
            if key != "max_completion_tokens"
        }
        serialized = json.dumps(payload_without_completion, ensure_ascii=False, separators=(",", ":"))
        return cls._estimate_text_tokens(serialized)

    def _fit_completion_budget(self, payload: dict[str, Any]) -> None:
        if self.max_completion_tokens is None or self.max_request_tokens is None:
            return

        prompt_tokens = self._estimate_payload_tokens(payload)
        available_completion_tokens = self.max_request_tokens - prompt_tokens - _TOKEN_BUDGET_BUFFER
        if available_completion_tokens < _MIN_COMPLETION_TOKENS:
            raise LLMProviderError(
                "Groq request is too large for the configured token-per-minute budget. "
                f"Estimated prompt tokens: {prompt_tokens}, "
                f"GROQ_MAX_REQUEST_TOKENS={self.max_request_tokens}. "
                "Shorten the prompt or raise GROQ_MAX_REQUEST_TOKENS for a higher Groq tier."
            )

        payload["max_completion_tokens"] = min(self.max_completion_tokens, available_completion_tokens)

    def _build_payload(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
        response_format: dict[str, Any] | None | object = _DEFAULT_RESPONSE_FORMAT,
    ) -> dict[str, Any]:
        resolved_response_format = (
            self._response_format(schema=schema, schema_name=schema_name)
            if response_format is _DEFAULT_RESPONSE_FORMAT
            else response_format
        )
        user_prompt = prompt
        if not isinstance(resolved_response_format, dict) or resolved_response_format.get("type") != _JSON_SCHEMA_RESPONSE_FORMAT:
            user_prompt = self._prompt_with_schema(prompt, schema=schema, schema_name=schema_name)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }
        if self.max_completion_tokens is not None:
            payload["max_completion_tokens"] = self.max_completion_tokens
        if isinstance(resolved_response_format, dict):
            payload["response_format"] = resolved_response_format
        self._fit_completion_budget(payload)
        return payload

    @staticmethod
    def _should_retry_with_json_object(payload: dict[str, Any], status_code: int, error_text: str) -> bool:
        response_format = payload.get("response_format")
        if not isinstance(response_format, dict) or response_format.get("type") != _JSON_SCHEMA_RESPONSE_FORMAT:
            return False
        if status_code != 400:
            return False
        normalized_error = error_text.lower()
        return (
            "json_schema" in normalized_error
            and "response_format" in normalized_error
        ) or (
            "json_validate_failed" in normalized_error
            or "generated json does not match" in normalized_error
        )

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

        payload = self._build_payload(system=system, prompt=prompt, schema=schema, schema_name=schema_name)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        attempted_json_object_fallback = False

        while True:
            try:
                client_options: dict[str, Any] = {"timeout": self.timeout_seconds}
                if self.transport is not None:
                    client_options["transport"] = self.transport

                async with httpx.AsyncClient(**client_options) as client:
                    response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                break
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("Groq request timed out") from exc
            except httpx.HTTPStatusError as exc:
                error_text = exc.response.text[:_ERROR_BODY_LIMIT]
                if exc.response.status_code == 429:
                    raise LLMRateLimitError("Groq free API limit reached. Please try again later.") from exc
                if (
                    self.response_format_mode == "auto"
                    and not attempted_json_object_fallback
                    and self._should_retry_with_json_object(payload, exc.response.status_code, error_text)
                ):
                    attempted_json_object_fallback = True
                    payload = self._build_payload(
                        system=system,
                        prompt=prompt,
                        schema=schema,
                        schema_name=schema_name,
                        response_format={"type": _JSON_OBJECT_RESPONSE_FORMAT},
                    )
                    continue
                raise LLMProviderError(f"Groq returned HTTP {exc.response.status_code}: {error_text}") from exc
            except httpx.HTTPError as exc:
                raise LLMProviderError(f"Groq request failed: {exc}") from exc

        body = response.json()
        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("Groq response did not include choices[0].message.content") from exc

        if isinstance(choice, dict) and choice.get("finish_reason") == "length":
            limit_hint = (
                f"GROQ_MAX_COMPLETION_TOKENS={self.max_completion_tokens}"
                if self.max_completion_tokens is not None
                else "the configured Groq completion token limit"
            )
            raise LLMProviderError(
                f"Groq stopped before completing the response because {limit_hint} was reached. "
                "Increase GROQ_MAX_COMPLETION_TOKENS or shorten the prompt."
            )

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Groq response content was empty")

        return LLMResponse(content=content, model=body.get("model", self.model), provider="groq", raw_metadata=body)
