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
    assert payload["max_completion_tokens"] == 5000
    assert "TestOutput 구조의 JSON 객체만 반환" in payload["messages"][1]["content"]
    assert "JSON Schema:" not in payload["messages"][1]["content"]


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
    assert "TestOutput 구조의 JSON 객체만 반환" in requests[1]["messages"][1]["content"]
    assert "JSON Schema:" not in requests[1]["messages"][1]["content"]
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
            headers={"Retry-After": "120"},
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

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "rate limit exceeded" in message
    assert "type=rate_limit_error" in message
    assert "Retry after 120 seconds" in message


@pytest.mark.asyncio
async def test_groq_waits_and_retries_short_tpm_rate_limit() -> None:
    requests: list[dict] = []
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "35"},
                json={
                    "error": {
                        "message": (
                            "Rate limit reached for model `llama-3.1-8b-instant` on tokens per minute "
                            "(TPM): Limit 6000, Used 4416, Requested 5006. Please try again in 34.22s."
                        ),
                        "type": "tokens",
                        "code": "rate_limit_exceeded",
                    }
                },
            )
        return _chat_completion(model="retry-model")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert len(requests) == 2
    assert sleeps == [35.0]
    assert response.model == "retry-model"


@pytest.mark.asyncio
async def test_groq_parses_try_again_delay_when_retry_after_header_is_missing() -> None:
    requests: list[dict] = []
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(
                429,
                json={
                    "error": {
                        "message": (
                            "Rate limit reached on tokens per minute: Limit 6000, Used 4416, Requested 5006. "
                            "Please try again in 34.22s."
                        ),
                        "type": "tokens",
                        "code": "rate_limit_exceeded",
                    }
                },
            )
        return _chat_completion(model="retry-model")

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert len(requests) == 2
    assert sleeps == [34.22]
    assert response.model == "retry-model"


@pytest.mark.asyncio
async def test_groq_raises_rate_limit_error_for_blocked_spend_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "API access blocked by spend limit",
                    "type": "invalid_request_error",
                    "code": "blocked_api_access",
                }
            },
        )

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="openai/gpt-oss-20b",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "spend limit" in message
    assert "code=blocked_api_access" in message


@pytest.mark.asyncio
async def test_groq_retries_oversized_tpm_request_with_reported_limit() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        if len(requests) > 1:
            return _chat_completion(model="fallback-model")

        return httpx.Response(
            413,
            json={
                "error": {
                    "message": (
                        "Request too large for model `llama-3.1-8b-instant` on tokens per minute "
                        "(TPM): Limit 6000, Requested 7027, please reduce your message size and try again."
                    ),
                    "type": "tokens",
                    "code": "rate_limit_exceeded",
                }
            },
        )

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        max_completion_tokens=4096,
        max_request_tokens=8000,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate(
        system="system",
        prompt="a" * 8000,
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        schema_name="TestOutput",
    )

    assert len(requests) == 2
    assert requests[0]["max_completion_tokens"] == 4096
    assert requests[1]["max_completion_tokens"] < requests[0]["max_completion_tokens"]
    assert GroqProvider._estimate_payload_tokens(requests[1]) + requests[1]["max_completion_tokens"] <= 6000
    assert response.model == "fallback-model"


@pytest.mark.asyncio
async def test_groq_raises_rate_limit_error_when_tpm_retry_still_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            413,
            json={
                "error": {
                    "message": (
                        "Request too large for model `llama-3.1-8b-instant` on tokens per minute "
                        "(TPM): Limit 6000, Requested 7027, please reduce your message size and try again."
                    ),
                    "type": "tokens",
                    "code": "rate_limit_exceeded",
                }
            },
        )

    provider = GroqProvider(
        api_key="test-key",
        base_url="http://groq.test/openai/v1",
        model="llama-3.1-8b-instant",
        max_completion_tokens=4096,
        max_request_tokens=8000,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "Limit 6000" in message
    assert "Requested 7027" in message
    assert "code=rate_limit_exceeded" in message


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
