"""Tests for the service launcher."""

import pytest
import asyncio
import aiohttp
from pathlib import Path
import os
import sys
import json
import tempfile
import logging
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from src.core.launcher import ServiceLauncher
from src.core.config import ConfigManager, AppConfig

@pytest.fixture
def temp_config(temp_workspace):
    """Create a temporary config file for testing."""
    config_path = temp_workspace / "config.json"
    config = {
        "ports": {
            "ollama": 11434,
            "api": 8000,
            "streamlit": 8501
        },
        "hosts": {
            "ollama": "localhost",
            "api": "localhost",
            "streamlit": "localhost"
        },
        "paths": {
            "ollama": None,
            "models": str(temp_workspace / "models"),
            "cache": str(temp_workspace / "cache"),
            "logs": str(temp_workspace / "logs")
        },
        "models": {
            "mistral": {
                "temp": 0.7,
                "max_tokens": 500,
                "context_window": 4096
            }
        },
        "auto_open_browser": False,
        "default_model": "mistral",
        "log_level": "info"
    }
    with open(config_path, 'w') as f:
        json.dump(config, f)
    return config_path

@asynccontextmanager
async def create_launcher(config_path):
    """Create and cleanup a ServiceLauncher instance."""
    launcher = ServiceLauncher(config_path=config_path)
    try:
        yield launcher
    finally:
        await launcher.stop_services()
        # Wait for processes to fully terminate
        await asyncio.sleep(0.5)

@pytest.mark.asyncio
async def test_start_api(temp_config):
    """Test starting the API server."""
    async with create_launcher(temp_config) as launcher:
        started = await launcher.start_api()
        assert started is True
        
        # Verify API is running
        async with aiohttp.ClientSession() as session:
            for _ in range(3):  # Retry a few times
                try:
                    async with session.get(
                        f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/health"
                    ) as response:
                        assert response.status == 200
                        break
                except aiohttp.ClientError:
                    await asyncio.sleep(0.5)
            else:
                pytest.fail("API server failed to respond")

@pytest.mark.asyncio
async def test_start_ui(temp_config):
    """Test starting the UI server."""
    async with create_launcher(temp_config) as launcher:
        started = await launcher.start_ui()
        assert started is True
        assert launcher.processes.get('ui') is not None
        assert launcher.processes['ui'].returncode is None

@pytest.mark.asyncio
async def test_run_services(temp_config):
    """Test running all services."""
    async with create_launcher(temp_config) as launcher:
        # Create an event to signal when services are ready
        ready_event = asyncio.Event()
        
        async def check_services():
            try:
                async with aiohttp.ClientSession() as session:
                    for _ in range(5):  # 5 retries
                        try:
                            async with session.get(
                                f"http://{launcher.config.hosts.api}:{launcher.config.ports.api}/health"
                            ) as response:
                                if response.status == 200:
                                    if launcher.processes.get('ui') and launcher.processes['ui'].returncode is None:
                                        ready_event.set()
                                        return
                        except aiohttp.ClientError:
                            pass
                        await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Error checking services: {e}")
        
        # Start services and checker in parallel
        run_task = asyncio.create_task(launcher.run())
        check_task = asyncio.create_task(check_services())
        
        try:
            # Wait for services to be ready or timeout
            await asyncio.wait_for(ready_event.wait(), timeout=15.0)
            
            # Verify services are running
            assert launcher.processes.get('ui') is not None, "UI server not started"
            assert launcher.processes['ui'].returncode is None, "UI server terminated"
            
            # Test API health
            assert await launcher.check_api_health(retries=3), "API health check failed"
            
        except asyncio.TimeoutError:
            pytest.fail("Services failed to start within timeout")
        finally:
            # Clean up
            for task in [check_task, run_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

@pytest.mark.asyncio
async def test_graceful_shutdown(temp_config):
    """Test graceful shutdown of services."""
    async with create_launcher(temp_config) as launcher:
        # Start services
        await launcher.start_api()
        await launcher.start_ui()
        
        # Verify services are running
        assert await launcher.check_api_health(), "API not healthy before shutdown"
        assert launcher.processes.get('ui') is not None, "UI not running before shutdown"
        
        # Stop services
        await launcher.stop_services()
        
        # Verify services are stopped
        assert not await launcher.check_api_health(retries=1), "API still running after shutdown"
        assert launcher.processes.get('ui') is None or launcher.processes['ui'].returncode is not None, "UI still running after shutdown"

@pytest.mark.asyncio
async def test_port_check(temp_config):
    """Test port availability checking."""
    async with create_launcher(temp_config) as launcher:
        # Test with available port
        assert await launcher.check_port_available(8000) is True
        
        # Start API service
        await launcher.start_api()
        await asyncio.sleep(0.5)  # Give the server time to start
        
        # Test with occupied port
        assert await launcher.check_port_available(8000) is False

@pytest.mark.asyncio
async def test_error_handling(temp_config):
    """Test error handling in service management."""
    async with create_launcher(temp_config) as launcher:
        # Test invalid port
        launcher.config.ports.api = -1
        with pytest.raises(ValueError):
            await launcher.start_api()
        
        # Test invalid host
        launcher.config.hosts.api = ""
        with pytest.raises(ValueError):
            await launcher.start_api()

def test_config_loading(temp_config):
    """Test configuration loading."""
    launcher = ServiceLauncher(config_path=temp_config)
    assert isinstance(launcher.config, AppConfig)
    assert launcher.config.ports.api == 8000
    assert launcher.config.default_model == "mistral"
    assert launcher.config.models["mistral"].temp == 0.7

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 