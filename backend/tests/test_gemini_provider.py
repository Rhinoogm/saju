import json

import httpx
import pytest

from app.services.llm.base import LLMProviderError, LLMRateLimitError, LLMServiceUnavailableError
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
async def test_gemini_reuses_injected_async_client_without_closing_it() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _generate_content_response(model="gemini-reused-client")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider(
            api_key="test-key",
            base_url="http://gemini.test/v1beta",
            client=client,
        )

        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")
        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

        assert len(requests) == 2
        assert client.is_closed is False


@pytest.mark.asyncio
async def test_gemini_uses_per_call_max_output_token_override() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = request.content
        return _generate_content_response()

    provider = GeminiProvider(
        api_key="test-key",
        base_url="http://gemini.test/v1beta",
        max_output_tokens=5000,
        transport=httpx.MockTransport(handler),
    )

    await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object"},
        schema_name="TestSchema",
        max_output_tokens=1200,
    )

    payload = json.loads(captured["payload"])
    assert payload["generationConfig"]["maxOutputTokens"] == 1200


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
async def test_gemini_retries_transient_503_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                503,
                json={
                    "error": {
                        "code": 503,
                        "message": "This model is currently experiencing high demand. Please try again later.",
                        "status": "UNAVAILABLE",
                    }
                },
            )
        return _generate_content_response(model="gemini-retry")

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    provider = GeminiProvider(
        api_key="test-key",
        base_url="http://gemini.test/v1beta",
        transport=httpx.MockTransport(handler),
        transient_retry_seconds=0.25,
        sleep=sleep,
    )

    response = await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

    assert response.model == "gemini-retry"
    assert calls == 2
    assert sleeps == [0.25]


@pytest.mark.asyncio
async def test_gemini_reports_friendly_error_after_transient_503_retries() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            503,
            json={
                "error": {
                    "code": 503,
                    "message": "This model is currently experiencing high demand. Please try again later.",
                    "status": "UNAVAILABLE",
                }
            },
        )

    async def sleep(seconds: float) -> None:
        return None

    provider = GeminiProvider(
        api_key="test-key",
        base_url="http://gemini.test/v1beta",
        transport=httpx.MockTransport(handler),
        max_transient_retries=1,
        transient_retry_seconds=0,
        sleep=sleep,
    )

    with pytest.raises(LLMServiceUnavailableError) as exc_info:
        await provider.generate(system="system", prompt="prompt", schema={"type": "object"}, schema_name="TestSchema")

    assert calls == 2
    assert "계정 사용량 한도와는 별개" in str(exc_info.value)
    assert "사용량이 많아" not in str(exc_info.value)


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
