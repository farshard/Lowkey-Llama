"""Tests for the system orchestrator."""

import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.core.orchestrator import SystemOrchestrator

@pytest.fixture
def orchestrator():
    """Create a test orchestrator instance."""
    return SystemOrchestrator(project_root=Path(__file__).parent.parent)

@pytest.mark.asyncio
async def test_check_port_available(orchestrator):
    """Test port availability check when port is free."""
    assert await orchestrator._check_port(12345)

@pytest.mark.asyncio
async def test_check_port_in_use(orchestrator):
    """Test port availability check when port is in use."""
    import socket
    
    # Bind a port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 12346))
    
    try:
        assert not await orchestrator._check_port(12346, retries=1)
    finally:
        s.close()

@pytest.mark.asyncio
async def test_ensure_dependencies_success(orchestrator):
    """Test successful dependency check."""
    with patch.object(orchestrator.dependency_manager, 'ensure_dependencies', return_value=True):
        assert await orchestrator.ensure_dependencies()

@pytest.mark.asyncio
async def test_ensure_dependencies_failure(orchestrator):
    """Test failed dependency check."""
    with patch.object(orchestrator.dependency_manager, 'ensure_dependencies', return_value=False):
        assert not await orchestrator.ensure_dependencies()

@pytest.mark.asyncio
async def test_ensure_ollama_success(orchestrator):
    """Test successful Ollama initialization."""
    # Mock Ollama server and health check
    with patch.object(orchestrator.ollama_server, 'start', return_value=True), \
         patch.object(orchestrator.system_init.ollama, 'health_check', AsyncMock(return_value=True)), \
         patch.object(orchestrator.system_init.ollama, 'list_models', AsyncMock(return_value=['mistral'])), \
         patch.object(orchestrator.system_init.ollama, 'generate', AsyncMock(return_value="Hello")):
        assert await orchestrator.ensure_ollama()

@pytest.mark.asyncio
async def test_ensure_ollama_failure(orchestrator):
    """Test failed Ollama initialization."""
    with patch.object(orchestrator.ollama_server, 'start', return_value=False):
        assert not await orchestrator.ensure_ollama()

@pytest.mark.asyncio
async def test_ensure_api_server_success(orchestrator):
    """Test successful API server initialization."""
    # Mock port check and server start
    with patch.object(orchestrator, '_check_port', AsyncMock(return_value=True)), \
         patch.object(orchestrator.system_init.api_server, 'start', AsyncMock()), \
         patch.object(orchestrator.system_init.api_server, 'health_check', AsyncMock(return_value=True)):
        assert await orchestrator.ensure_api_server()

@pytest.mark.asyncio
async def test_ensure_api_server_port_in_use(orchestrator):
    """Test API server initialization with port conflict."""
    with patch.object(orchestrator, '_check_port', AsyncMock(return_value=False)):
        assert not await orchestrator.ensure_api_server()

@pytest.mark.asyncio
async def test_ensure_ui_server_success(orchestrator):
    """Test successful UI server initialization."""
    # Mock port check and server start
    with patch.object(orchestrator, '_check_port', AsyncMock(return_value=True)), \
         patch.object(orchestrator.system_init.ui_server, 'start', AsyncMock()):
        assert await orchestrator.ensure_ui_server()

@pytest.mark.asyncio
async def test_ensure_ui_server_port_in_use(orchestrator):
    """Test UI server initialization with port conflict."""
    with patch.object(orchestrator, '_check_port', AsyncMock(return_value=False)):
        assert not await orchestrator.ensure_ui_server()

@pytest.mark.asyncio
async def test_initialize_success(orchestrator):
    """Test successful system initialization."""
    # Mock all component initializations
    with patch.object(orchestrator, 'ensure_dependencies', AsyncMock(return_value=True)), \
         patch.object(orchestrator, 'ensure_ollama', AsyncMock(return_value=True)), \
         patch.object(orchestrator, 'ensure_api_server', AsyncMock(return_value=True)), \
         patch.object(orchestrator, 'ensure_ui_server', AsyncMock(return_value=True)), \
         patch.object(orchestrator.system_init, '_track', AsyncMock(return_value={})):
        assert await orchestrator.initialize()

@pytest.mark.asyncio
async def test_initialize_failure(orchestrator):
    """Test system initialization with component failure."""
    # Mock dependency check failure
    with patch.object(orchestrator, 'ensure_dependencies', AsyncMock(return_value=False)), \
         patch.object(orchestrator, 'cleanup', AsyncMock()):
        assert not await orchestrator.initialize()

@pytest.mark.asyncio
async def test_cleanup(orchestrator):
    """Test system cleanup."""
    # Mock server stop methods
    with patch.object(orchestrator.system_init.ui_server, 'stop', AsyncMock()), \
         patch.object(orchestrator.system_init.api_server, 'stop', AsyncMock()), \
         patch.object(orchestrator.ollama_server, 'stop'):
        await orchestrator.cleanup()
        # Verify all stop methods were called
        orchestrator.system_init.ui_server.stop.assert_called_once()
        orchestrator.system_init.api_server.stop.assert_called_once()
        orchestrator.ollama_server.stop.assert_called_once() 