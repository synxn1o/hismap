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


@pytest.mark.asyncio
async def test_chat_with_tools(llm):
    """Test that chat_with_tools passes tools and returns structured response."""
    mock_message = AsyncMock()
    mock_message.content = '{"result": "ok"}'
    mock_message.tool_calls = None
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=mock_message)]

    tools = [{"type": "web_search", "max_keyword": 6, "force_search": False, "limit": 6}]

    with patch.object(llm.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response) as mock_create:
        result = await llm.chat_with_tools("test prompt", tools=tools, system="sys")

    assert result == '{"result": "ok"}'
    call_args = mock_create.call_args
    assert call_args.kwargs["tools"] == tools
    assert call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_chat_with_tools_no_tools(llm):
    """Test chat_with_tools without tools parameter."""
    mock_message = AsyncMock()
    mock_message.content = '{"result": "ok"}'
    mock_message.tool_calls = None
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=mock_message)]

    with patch.object(llm.client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response) as mock_create:
        result = await llm.chat_with_tools("test prompt")

    assert result == '{"result": "ok"}'
    call_args = mock_create.call_args
    assert "tools" not in call_args.kwargs
    assert "response_format" not in call_args.kwargs
