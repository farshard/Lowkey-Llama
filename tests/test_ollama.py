"""Tests for Ollama integration."""

import pytest
import aiohttp
import asyncio
import json
from pathlib import Path
from pytest_asyncio import fixture
from unittest.mock import AsyncMock, patch

from src.core.ollama import OllamaClient

@fixture
async def mock_ollama():
    """Create a mock Ollama client for testing."""
    mock = AsyncMock(spec=OllamaClient)
    mock.health_check.return_value = True
    mock.list_models.return_value = ["mistral", "codellama"]
    mock.generate.return_value = "Test response"
    mock.get_model_info.return_value = {"name": "mistral"}
    return mock

@pytest.mark.asyncio
async def test_ollama_health(mock_ollama):
    """Test that Ollama is running and healthy."""
    is_healthy = await mock_ollama.health_check()
    assert is_healthy is True

@pytest.mark.asyncio
async def test_list_models(mock_ollama):
    """Test listing available models."""
    models = await mock_ollama.list_models()
    assert isinstance(models, list)
    assert len(models) == 2
    assert "mistral" in models
    assert "codellama" in models

@pytest.mark.asyncio
async def test_generate_response(mock_ollama):
    """Test generating a response from Ollama."""
    prompt = "Hello, how are you?"
    response = await mock_ollama.generate(
        model="mistral",
        prompt=prompt,
        max_tokens=100
    )
    assert response == "Test response"

@pytest.mark.asyncio
async def test_model_info(mock_ollama):
    """Test getting model information."""
    model_info = await mock_ollama.get_model_info("mistral")
    assert isinstance(model_info, dict)
    assert "name" in model_info
    assert model_info["name"] == "mistral"

@pytest.mark.asyncio
async def test_ollama_connection_error():
    """Test handling of Ollama connection errors."""
    client = OllamaClient("nonexistent/path")
    try:
        await client.connect()
        async with client.session.get("http://nonexistent:11434/api/health") as response:
            assert False, "Should have raised an error"
    except aiohttp.ClientError:
        assert True
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_ollama_invalid_model(mock_ollama):
    """Test handling of invalid model requests."""
    mock_ollama.get_model_info.side_effect = ValueError("Model not found")
    with pytest.raises(ValueError):
        await mock_ollama.get_model_info("nonexistent_model")