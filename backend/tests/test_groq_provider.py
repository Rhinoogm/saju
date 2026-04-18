import json

import httpx
import pytest

from app.services.llm.base import LLMRateLimitError
from app.services.llm.groq_provider import GroqProvider


def _chat_completion(content: str = '{"ok":true}', *, model: str = "test-model") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": {"content": content}}],
        },
    )


@pytest.mark.asyncio
async def test_groq_auto_uses_json_object_for_models_without_json_schema_support() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _chat_completion()

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        transport=httpx.MockTransport(handler),
    )

    await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    payload = requests[0]
    assert payload["response_format"] == {"type": "json_object"}
    assert "JSON Schema:" in payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_groq_auto_uses_strict_json_schema_for_supported_models() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _chat_completion()

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        transport=httpx.MockTransport(handler),
    )

    await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    response_format = requests[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == "TestOutput"
    assert "JSON Schema:" not in requests[0]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_groq_auto_retries_json_schema_400_with_json_object() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "This model does not support response_format json_schema",
                        "type": "invalid_request_error",
                        "param": "response_format",
                    }
                },
            )
        return _chat_completion(model="fallback-model")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert len(requests) == 2
    assert requests[0]["response_format"]["type"] == "json_schema"
    assert requests[1]["response_format"] == {"type": "json_object"}
    assert "JSON Schema:" in requests[1]["messages"][1]["content"]
    assert response.model == "fallback-model"


@pytest.mark.asyncio
async def test_groq_auto_retries_json_schema_validation_400_with_json_object() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "Generated JSON does not match the expected schema.",
                        "type": "invalid_request_error",
                        "code": "json_validate_failed",
                    }
                },
            )
        return _chat_completion(model="fallback-model")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert len(requests) == 2
    assert requests[0]["response_format"]["type"] == "json_schema"
    assert requests[1]["response_format"] == {"type": "json_object"}
    assert response.model == "fallback-model"


@pytest.mark.asyncio
async def test_groq_raises_rate_limit_error_for_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "rate limit exceeded",
                    "type": "rate_limit_error",
                }
            },
        )

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMRateLimitError):
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )
