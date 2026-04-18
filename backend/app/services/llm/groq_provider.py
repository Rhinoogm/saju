from __future__ import annotations

from typing import Any

import httpx

from app.services.llm.base import LLMProviderError, LLMResponse, LLMTimeoutError


class GroqProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
        model: str = "llama-3.1-8b-instant",
        timeout_seconds: float = 60.0,
        temperature: float = 0.25,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

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

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Groq request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Groq returned HTTP {exc.response.status_code}: {exc.response.text[:500]}") from exc
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
