import json

import httpx
import pytest

from app.services.llm.base import LLMProviderError, LLMRateLimitError
from app.services.llm.groq_provider import GroqProvider, _MIN_COMPLETION_TOKENS


def _chat_completion(content: str = '{"ok":true}', *, model: str = "test-model", finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
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
    assert payload["max_completion_tokens"] == 4096
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
async def test_groq_sends_configured_max_completion_tokens() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _chat_completion()

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        max_completion_tokens=2048,
        transport=httpx.MockTransport(handler),
    )

    await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert requests[0]["max_completion_tokens"] == 2048


@pytest.mark.asyncio
async def test_groq_caps_completion_tokens_to_fit_request_budget() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _chat_completion()

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        max_completion_tokens=1200,
        max_request_tokens=2000,
        transport=httpx.MockTransport(handler),
    )

    await provider.generate(
        system="system",
        prompt="a" * 4000,
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert _MIN_COMPLETION_TOKENS <= requests[0]["max_completion_tokens"] < 1200
    assert (
        GroqProvider._estimate_payload_tokens(requests[0])
        + requests[0]["max_completion_tokens"]
        <= 2000
    )


@pytest.mark.asyncio
async def test_groq_raises_clear_error_when_prompt_exceeds_request_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("oversized request should not be sent")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        max_completion_tokens=1200,
        max_request_tokens=1200,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(
            system="system",
            prompt="a" * 8000,
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "Groq request is too large" in message
    assert "GROQ_MAX_REQUEST_TOKENS=1200" in message


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


@pytest.mark.asyncio
async def test_groq_raises_clear_error_when_generation_hits_length_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_completion('{"ok":', finish_reason="length")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        max_completion_tokens=16,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "GROQ_MAX_COMPLETION_TOKENS=16" in message
    assert "shorten the prompt" in message
