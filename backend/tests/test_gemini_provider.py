import json

import httpx
import pytest

from app.services.llm.base import LLMProviderError, LLMRateLimitError
from app.services.llm.gemini_provider import GeminiProvider


def _generate_content_response(content: str = '{"ok":true}', *, model: str = "gemini-test") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "modelVersion": model,
            "candidates": [
                {
                    "content": {"parts": [{"text": content}]},
                    "finishReason": "STOP",
                }
            ],
        },
    )


@pytest.mark.asyncio
async def test_gemini_sends_response_json_schema() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-goog-api-key")
        captured["payload"] = request.content
        return _generate_content_response(model="gemini-2.5-flash-001")

    provider = GeminiProvider(
        api_key="test-key",
        base_url="http://gemini.test/v1beta",
        model="gemini-2.5-flash",
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            },
            "type": "object",
            "properties": {"item": {"$ref": "#/$defs/Item"}, "note": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
            "required": ["item", "note"],
        },
        schema_name="TestSchema",
    )

    payload = json.loads(captured["payload"])
    response_schema = payload["generationConfig"]["responseJsonSchema"]

    assert captured["url"] == "http://gemini.test/v1beta/models/gemini-2.5-flash:generateContent"
    assert captured["api_key"] == "test-key"
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert response_schema["properties"]["item"]["properties"]["name"]["type"] == "string"
    assert response_schema["properties"]["note"]["type"] == ["string", "null"]
    assert "$defs" not in response_schema
    assert response.provider == "gemini"
    assert response.model == "gemini-2.5-flash-001"


@pytest.mark.asyncio
async def test_gemini_requires_api_key() -> None:
    provider = GeminiProvider(api_key=None)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

    assert "GEMINI_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_raises_rate_limit_error_for_429() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}},
        )

    provider = GeminiProvider(api_key="test-key", base_url="http://gemini.test/v1beta", transport=httpx.MockTransport(handler))

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

    assert "Gemini API limit reached" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_raises_clear_error_when_generation_hits_length_limit() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": '{"ok":'}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ]
            },
        )

    provider = GeminiProvider(api_key="test-key", base_url="http://gemini.test/v1beta", transport=httpx.MockTransport(handler))

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

    assert "GEMINI_MAX_OUTPUT_TOKENS" in str(exc_info.value)
