import json

import httpx
import pytest

from app.services.llm.base import LLMProviderError
from app.services.llm.ollama_provider import OllamaProvider


def _stream_response(*events: dict) -> httpx.Response:
    content = "\n".join(json.dumps(event) for event in events)
    return httpx.Response(200, content=content)


@pytest.mark.asyncio
async def test_ollama_stream_http_error_reads_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://ollama.test/api/generate"
        return httpx.Response(500, text='{"error":"model crashed"}')

    provider = OllamaProvider(
        base_url="http://ollama.test",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object"},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "Ollama returned HTTP 500" in message
    assert "model crashed" in message
    assert "ResponseNotRead" not in message


@pytest.mark.asyncio
async def test_ollama_sends_num_predict_option() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return _stream_response(
            {"response": '{"ok":true}', "done": False},
            {"response": "", "done": True, "done_reason": "stop", "model": "test-model"},
        )

    provider = OllamaProvider(
        base_url="http://ollama.test",
        model="test-model",
        num_predict=2048,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate(
        system="system",
        prompt="prompt",
        schema={"type": "object"},
        schema_name="TestOutput",
    )

    assert requests[0]["options"]["num_predict"] == 2048
    assert response.content == '{"ok":true}'


@pytest.mark.asyncio
async def test_ollama_raises_clear_error_when_generation_hits_length_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _stream_response(
            {"response": '{"ok":', "done": False},
            {"response": "", "done": True, "done_reason": "length", "model": "test-model"},
        )

    provider = OllamaProvider(
        base_url="http://ollama.test",
        model="test-model",
        num_predict=16,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate(
            system="system",
            prompt="prompt",
            schema={"type": "object"},
            schema_name="TestOutput",
        )

    message = str(exc_info.value)
    assert "OLLAMA_NUM_PREDICT=16" in message
    assert "shorten the prompt" in message
