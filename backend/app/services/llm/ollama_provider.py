from __future__ import annotations

import json
from typing import Any, Literal

import httpx

from app.services.llm.base import LLMProviderError, LLMResponse, LLMTimeoutError

_ERROR_BODY_LIMIT = 500
_FORMAT_VOCAB_ERROR_SNIPPET = "failed to load model vocabulary required for format"


async def _response_error_text(response: httpx.Response, *, limit: int = _ERROR_BODY_LIMIT) -> str:
    try:
        content = response.content
    except httpx.ResponseNotRead:
        try:
            content = await response.aread()
        except (httpx.HTTPError, RuntimeError) as exc:
            return f"<failed to read response body: {exc}>"

    if not content:
        return "<empty response body>"

    encoding = response.encoding or "utf-8"
    return content.decode(encoding, errors="replace")[:limit]


class OllamaProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3:4b",
        timeout_seconds: float = 120.0,
        temperature: float = 0.4,
        format_mode: Literal["auto", "schema", "json", "none"] = "auto",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.format_mode = format_mode
        self.transport = transport

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/api"):
            return f"{self.base_url}/generate"
        return f"{self.base_url}/api/generate"

    def _build_payload(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
            },
        }

        if self.format_mode == "none":
            return payload
        if self.format_mode == "json":
            payload["format"] = "json"
            return payload
        if self.format_mode == "schema":
            payload["format"] = schema
            return payload

        # auto (default): try schema first, then optionally fall back to json
        payload["format"] = schema
        return payload

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
    ) -> LLMResponse:
        attempted_fallback = False
        payload = self._build_payload(system=system, prompt=prompt, schema=schema)

        while True:
            content_chunks: list[str] = []
            metadata: dict[str, Any] = {}

            try:
                client_options: dict[str, Any] = {"timeout": self.timeout_seconds}
                if self.transport is not None:
                    client_options["transport"] = self.transport

                async with httpx.AsyncClient(**client_options) as client:
                    async with client.stream("POST", self.endpoint, json=payload) as response:
                        if not response.is_success:
                            error_text = await _response_error_text(response)
                            raise LLMProviderError(f"Ollama returned HTTP {response.status_code}: {error_text}")

                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue

                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise LLMProviderError(f"Ollama returned invalid stream JSON: {line[:300]}") from exc

                            error = event.get("error")
                            if isinstance(error, str) and error:
                                raise LLMProviderError(f"Ollama returned an error: {error}")

                            chunk = event.get("response")
                            if isinstance(chunk, str):
                                content_chunks.append(chunk)

                            if event.get("done") is True:
                                metadata = {key: value for key, value in event.items() if key != "response"}
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("Ollama request timed out") from exc
            except httpx.HTTPStatusError as exc:
                error_text = await _response_error_text(exc.response)
                raise LLMProviderError(f"Ollama returned HTTP {exc.response.status_code}: {error_text}") from exc
            except httpx.HTTPError as exc:
                raise LLMProviderError(f"Ollama request failed: {exc}") from exc
            except LLMProviderError as exc:
                message = str(exc)
                if (
                    self.format_mode == "auto"
                    and not attempted_fallback
                    and _FORMAT_VOCAB_ERROR_SNIPPET in message
                    and payload.get("format") != "json"
                ):
                    attempted_fallback = True
                    payload = {**payload, "format": "json"}
                    continue
                raise

            content = "".join(content_chunks)
            if not content.strip():
                raise LLMProviderError("Ollama response did not include a non-empty 'response' field")

            metadata.pop("context", None)
            model = metadata.get("model")
            return LLMResponse(
                content=content,
                model=model if isinstance(model, str) else self.model,
                provider="ollama",
                raw_metadata=metadata,
            )
