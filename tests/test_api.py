"""Tests for the API server."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import FastAPI, HTTPException
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import json
from httpx import ASGITransport

from src.api.server import app, get_ollama_client
from src.core.ollama import OllamaClient

@pytest.fixture
def mock_ollama():
    """Create a mock Ollama client."""
    mock = MagicMock(spec=OllamaClient)
    mock.health_check = AsyncMock(return_value=True)
    mock.list_models = AsyncMock(return_value=["mistral", "codellama"])
    mock.generate = AsyncMock(return_value="Test response")
    mock.get_model_info = AsyncMock(return_value={"name": "mistral"})
    return mock

@pytest.fixture
def override_dependencies(mock_ollama):
    """Override FastAPI dependencies."""
    app.dependency_overrides[get_ollama_client] = lambda: mock_ollama
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(override_dependencies):
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

@pytest.mark.asyncio
async def test_health_check_async(async_client, mock_ollama):
    """Test the health check endpoint with async client."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_ollama.health_check.assert_awaited_once()

@pytest.mark.asyncio
async def test_health_check_sync(async_client):
    """Test the health check endpoint with sync-style test."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_models_endpoint_async(async_client, mock_ollama):
    """Test the models endpoint with async client."""
    response = await async_client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert data["models"] == ["mistral", "codellama"]
    mock_ollama.list_models.assert_awaited_once()

@pytest.mark.asyncio
async def test_models_endpoint_sync(async_client):
    """Test the models endpoint with sync-style test."""
    response = await async_client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert data["models"] == ["mistral", "codellama"]

@pytest.mark.asyncio
async def test_generate_endpoint_async(async_client, mock_ollama):
    """Test the generate endpoint with async client."""
    payload = {
        "prompt": "Hello, how are you?",
        "model": "mistral",
        "max_tokens": 100
    }
    response = await async_client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] == "Test response"
    mock_ollama.generate.assert_awaited_once_with(
        model=payload["model"],
        prompt=payload["prompt"],
        max_tokens=payload["max_tokens"]
    )

@pytest.mark.asyncio
async def test_generate_endpoint_sync(async_client):
    """Test the generate endpoint with sync-style test."""
    payload = {
        "prompt": "Hello, how are you?",
        "model": "mistral",
        "max_tokens": 100
    }
    response = await async_client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] == "Test response"

@pytest.mark.asyncio
async def test_generate_endpoint_validation(async_client):
    """Test input validation for generate endpoint."""
    # Test missing required fields
    response = await async_client.post("/generate", json={})
    assert response.status_code == 422

    # Test invalid model name
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "",
        "max_tokens": 100
    })
    assert response.status_code == 422

    # Test invalid max_tokens
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "mistral",
        "max_tokens": -1
    })
    assert response.status_code == 422

    # Test empty prompt
    response = await async_client.post("/generate", json={
        "prompt": "",
        "model": "mistral",
        "max_tokens": 100
    })
    assert response.status_code == 422

    # Test extremely large max_tokens
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "mistral",
        "max_tokens": 1000000
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_error_handling(async_client, mock_ollama):
    """Test error handling in API endpoints."""
    # Test Ollama service unavailable
    mock_ollama.health_check.side_effect = ConnectionError("Failed to connect")
    response = await async_client.get("/health")
    assert response.status_code == 503
    assert "Failed to connect" in response.json()["detail"]
    
    # Test model not found
    mock_ollama.generate.side_effect = ValueError("Model not found")
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "nonexistent",
        "max_tokens": 100
    })
    assert response.status_code == 404
    assert "Model not found" in response.json()["detail"]

    # Test generation timeout
    mock_ollama.generate.side_effect = asyncio.TimeoutError()
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "mistral",
        "max_tokens": 100
    })
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_concurrent_requests(async_client, mock_ollama):
    """Test handling of concurrent requests."""
    # Simulate slow response from Ollama
    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.1)
        return "Test response"
    
    mock_ollama.generate = AsyncMock(side_effect=slow_generate)
    
    # Make multiple concurrent requests
    payloads = [
        {
            "prompt": f"Test prompt {i}",
            "model": "mistral",
            "max_tokens": 100
        }
        for i in range(5)
    ]
    
    # Send requests concurrently
    tasks = [
        async_client.post("/generate", json=payload)
        for payload in payloads
    ]
    responses = await asyncio.gather(*tasks)
    
    # Verify all requests succeeded
    for response in responses:
        assert response.status_code == 200
        assert "response" in response.json()
    
    # Verify the mock was called the correct number of times
    assert mock_ollama.generate.await_count == len(payloads)

@pytest.mark.asyncio
async def test_model_info_validation(async_client, mock_ollama):
    """Test model information validation."""
    # Test with invalid model info
    mock_ollama.get_model_info.side_effect = ValueError("Invalid model")
    
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "invalid_model",
        "max_tokens": 100
    })
    assert response.status_code == 404
    assert "Invalid model" in response.json()["detail"]
    
    # Test with model info missing required fields
    mock_ollama.get_model_info.side_effect = None
    mock_ollama.get_model_info.return_value = {}
    
    response = await async_client.post("/generate", json={
        "prompt": "test",
        "model": "incomplete_model",
        "max_tokens": 100
    })
    assert response.status_code == 500
    assert "model info" in response.json()["detail"].lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 