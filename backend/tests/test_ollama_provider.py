import httpx
import pytest

from app.services.llm.base import LLMProviderError
from app.services.llm.ollama_provider import OllamaProvider


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
