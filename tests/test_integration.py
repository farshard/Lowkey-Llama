"""Integration tests for Local LLM Chat Interface."""

import pytest
import asyncio
import aiohttp
import json
from pathlib import Path
import sys
import logging
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from src.core.launcher import ServiceLauncher
from src.api.server import app
from src.core.ollama import OllamaClient

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_service_startup(temp_config):
    """Test complete service startup and interaction."""
    launcher = ServiceLauncher(config_path=temp_config)
    
    try:
        # Start all services
        run_task = asyncio.create_task(launcher.run())
        
        # Wait for services to be ready
        for _ in range(10):  # Try for 10 seconds
            if await launcher.check_api_health(retries=1):
                break
            await asyncio.sleep(1)
        else:
            pytest.fail("Services failed to start within timeout")
        
        # Verify UI is running
        assert launcher.processes.get('ui') is not None
        assert launcher.processes['ui'].returncode is None
        
        # Test API endpoints
        async with aiohttp.ClientSession() as session:
            # Health check
            async with session.get(
                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/health"
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "ok"
            
            # List models
            async with session.get(
                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/models"
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert "models" in data
            
            # Test generation endpoint
            payload = {
                "prompt": "Hello, how are you?",
                "model": launcher.config.default_model,
                "max_tokens": 100
            }
            async with session.post(
                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/generate",
                json=payload
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert "response" in data
                
    finally:
        # Cleanup
        await launcher.stop_services()
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_ollama_interaction(temp_config):
    """Test interaction between API and Ollama client."""
    launcher = ServiceLauncher(config_path=temp_config)
    
    try:
        # Start API service
        await launcher.start_api()
        
        # Wait for API to be ready
        assert await launcher.check_api_health(retries=3), "API failed to start"
        
        # Create Ollama client
        ollama = OllamaClient()
        
        # Test model operations
        models = await ollama.list_models()
        assert isinstance(models, list), "Failed to list models"
        
        if models:
            model_info = await ollama.get_model_info(models[0])
            assert isinstance(model_info, dict), "Failed to get model info"
            
            # Test generation through API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": "Test prompt",
                    "model": models[0],
                    "max_tokens": 50
                }
                async with session.post(
                    f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/generate",
                    json=payload
                ) as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "response" in data
                    assert isinstance(data["response"], str)
    
    finally:
        await launcher.stop_services()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_propagation(temp_config):
    """Test error handling and propagation between components."""
    launcher = ServiceLauncher(config_path=temp_config)
    
    try:
        # Start API service
        await launcher.start_api()
        assert await launcher.check_api_health(retries=3), "API failed to start"
        
        async with aiohttp.ClientSession() as session:
            # Test invalid model
            payload = {
                "prompt": "Test prompt",
                "model": "nonexistent_model",
                "max_tokens": 50
            }
            async with session.post(
                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/generate",
                json=payload
            ) as response:
                assert response.status == 404
                data = await response.json()
                assert "detail" in data
            
            # Test invalid parameters
            payload = {
                "prompt": "",  # Empty prompt
                "model": launcher.config.default_model,
                "max_tokens": -1  # Invalid tokens
            }
            async with session.post(
                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/generate",
                json=payload
            ) as response:
                assert response.status == 422
                data = await response.json()
                assert "detail" in data
    
    finally:
        await launcher.stop_services()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"]) 