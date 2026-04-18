from __future__ import annotations

import json
from typing import Any, Literal

import httpx

from app.services.llm.base import LLMProviderError, LLMRateLimitError, LLMResponse, LLMTimeoutError

_ERROR_BODY_LIMIT = 500
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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.response_format_mode = response_format_mode
        self.json_schema_strict = json_schema_strict
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
        if isinstance(resolved_response_format, dict):
            payload["response_format"] = resolved_response_format
        return payload

    @staticmethod
    def _should_retry_with_json_object(payload: dict[str, Any], status_code: int, error_text: str) -> bool:
        response_format = payload.get("response_format")
        if not isinstance(response_format, dict) or response_format.get("type") != _JSON_SCHEMA_RESPONSE_FORMAT:
            return False
        if status_code != 400:
            return False
        normalized_error = error_text.lower()
        return "json_schema" in normalized_error and "response_format" in normalized_error

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
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("Groq response did not include choices[0].message.content") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Groq response content was empty")

        return LLMResponse(content=content, model=body.get("model", self.model), provider="groq", raw_metadata=body)
