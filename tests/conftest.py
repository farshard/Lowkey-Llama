"""Pytest configuration file."""

import os
import sys
import json
import tempfile
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from src.core.ollama import OllamaClient

def pytest_configure(config):
    """Configure pytest."""
    # Add markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    
    # Set asyncio mode to auto
    config.option.asyncio_mode = "auto"

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
async def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()
    return mock

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create necessary subdirectories
    (workspace / "models").mkdir()
    (workspace / "logs").mkdir()
    (workspace / "cache").mkdir()
    (workspace / "src").mkdir()
    (workspace / "src/api").mkdir()
    (workspace / "src/ui").mkdir()
    (workspace / "src/core").mkdir()
    
    # Create minimal required files
    (workspace / "src/api/server.py").touch()
    (workspace / "src/ui/app.py").touch()
    
    # Add workspace to Python path
    sys.path.insert(0, str(workspace))
    
    return workspace

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

@pytest.fixture
def override_dependencies(mock_ollama):
    """Override FastAPI dependencies."""
    from src.api.server import app, get_ollama_client
    app.dependency_overrides[get_ollama_client] = lambda: mock_ollama
    yield
    app.dependency_overrides.clear()

# Configure asyncio for testing
pytest_plugins = ["pytest_asyncio"] 