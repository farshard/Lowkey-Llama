"""Tests for the Ollama client functionality."""

import asyncio
import json
import logging
import pytest
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from src.core.ollama import OllamaClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture
async def ollama_client():
    """Fixture for creating and cleaning up an Ollama client."""
    client = OllamaClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_health_check(ollama_client):
    """Test the Ollama server health check."""
    healthy = await ollama_client.health_check()
    assert healthy, "Ollama server should be healthy"

@pytest.mark.asyncio
async def test_list_models(ollama_client):
    """Test listing available models."""
    models = await ollama_client.list_models()
    assert isinstance(models, list), "Models should be returned as a list"
    assert len(models) > 0, "At least one model should be available"

@pytest.mark.asyncio
@pytest.mark.parametrize("model_name", ["mistral", "mistral-fixed"])
async def test_chat_response(ollama_client, model_name):
    """Test chat functionality with different models."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, tell me about dogs in one sentence."}
    ]
    
    options = {
        "temperature": 0.7,
        "num_predict": 100,
        "top_p": 0.95,
        "top_k": 60,
        "repeat_penalty": 1.18
    }
    
    response = await ollama_client.chat(
        model=model_name,
        messages=messages,
        options=options
    )
    
    assert response, f"Should get a response from {model_name}"
    assert "response" in response, f"Response from {model_name} should contain 'response' key"
    assert isinstance(response["response"], str), f"Response from {model_name} should be a string"
    
    # Log response for manual verification
    logger.info(f"{model_name} response: {json.dumps(response, indent=2)}")

@pytest.mark.asyncio
async def test_mistral_fixed_improvements(ollama_client):
    """Test specific improvements in mistral-fixed model."""
    # Test with a prompt that previously caused truncation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me about baseball in three sentences."}
    ]
    
    # Get responses from both models for comparison
    standard_response = await ollama_client.chat(
        model="mistral",
        messages=messages
    )
    
    fixed_response = await ollama_client.chat(
        model="mistral-fixed",
        messages=messages
    )
    
    # Compare response lengths
    standard_length = len(standard_response["response"].split())
    fixed_length = len(fixed_response["response"].split())
    
    logger.info(f"Standard response length: {standard_length} words")
    logger.info(f"Fixed response length: {fixed_length} words")
    
    # The fixed model should generally provide more detailed responses
    assert fixed_length >= standard_length, (
        "mistral-fixed should provide more detailed responses than standard mistral"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"]) 