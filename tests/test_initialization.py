import pytest
from unittest.mock import AsyncMock, patch
from src.core.launcher import SystemInit
import subprocess

@pytest.mark.asyncio
async def test_full_initialization():
    """Test successful initialization sequence"""
    mock_ollama = AsyncMock()
    mock_ollama.health_check.return_value = True
    mock_ollama.list_models.return_value = ["mistral"]
    
    with patch('src.core.launcher.OllamaClient', return_value=mock_ollama):
        system = SystemInit()
        result = await system.run_initialization()
        
        assert result is True
        mock_ollama.health_check.assert_awaited_once()
        mock_ollama.list_models.assert_awaited_once()

@pytest.mark.asyncio
async def test_port_conflict_handling():
    """Test port conflict detection and handling"""
    system = SystemInit()
    
    with patch('src.core.services.ServiceManager.is_port_in_use') as mock_port:
        mock_port.return_value = True
        result = await system.check_ports()
        
        assert result is False 

@pytest.mark.asyncio
async def test_failed_ollama_startup():
    """Test Ollama startup failure handling"""
    mock_service = AsyncMock()
    mock_service.start_ollama.return_value = False
    
    with patch('src.core.launcher.ServiceManager', return_value=mock_service):
        system = SystemInit()
        result = await system.run_initialization()
        assert result is False
        mock_service.start_ollama.assert_awaited_once()

@pytest.mark.asyncio
async def test_retry_failed_dependency_installation():
    """Test dependency installation retry logic"""
    with patch('subprocess.check_call') as mock_install:
        mock_install.side_effect = [
            subprocess.CalledProcessError(1, 'cmd'),
            subprocess.CalledProcessError(1, 'cmd'),
            None  # Success on third try
        ]
        assert install_packages(['test-package']) is True

    with patch('subprocess.check_call') as mock_install:
        mock_install.side_effect = [
            subprocess.CalledProcessError(1, 'cmd'),
            subprocess.CalledProcessError(1, 'cmd'),
            subprocess.CalledProcessError(1, 'cmd')
        ]
        assert install_packages(['test-package']) is False 