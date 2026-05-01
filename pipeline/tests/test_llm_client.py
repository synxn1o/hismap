import pytest
from unittest.mock import AsyncMock, patch

from pipeline.core.llm_client import LLMClient


@pytest.fixture
def llm():
    config = {
        "llm": {
            "base_url": "http://localhost:8000/v1",
            "api_key": "test-key",
            "model": "test-model",
            "max_tokens": 100,
            "temperature": 0.0,
        }
    }
    return LLMClient(config)


@pytest.mark.asyncio
async def test_chat(llm):
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Hello world"))]
    with patch.object(llm.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
        result = await llm.chat("test prompt")
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_extract_json_strips_fences(llm):
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content='```json\n{"key": "value"}\n```'))]
    with patch.object(llm.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
        result = await llm.extract_json("test prompt")
    assert result == '{"key": "value"}'
