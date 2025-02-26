import pytest
from pathlib import Path
import json
import tempfile
from src.core.config import ConfigManager, ModelConfig, AppConfig

@pytest.fixture
def temp_config():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
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
                "models": "models",
                "cache": "cache",
                "logs": "logs"
            },
            "models": {
                "mistral": {
                    "temp": 0.7,
                    "max_tokens": 500,
                    "context_window": 4096
                }
            },
            "auto_open_browser": True,
            "default_model": "mistral",
            "log_level": "info"
        }
        json.dump(config, f)
        f.flush()
        yield f.name
    Path(f.name).unlink()

def test_config_loading(temp_config):
    """Test basic configuration loading"""
    config_manager = ConfigManager(config_path=temp_config)
    assert isinstance(config_manager.config, AppConfig)
    assert config_manager.config.ports.ollama == 11434
    assert config_manager.config.default_model == "mistral"

def test_model_config(temp_config):
    """Test model configuration access"""
    config_manager = ConfigManager(config_path=temp_config)
    model_config = config_manager.get_model_config("mistral")
    assert isinstance(model_config, ModelConfig)
    assert model_config.temp == 0.7
    assert model_config.max_tokens == 500

def test_invalid_model(temp_config):
    """Test accessing non-existent model"""
    config_manager = ConfigManager(config_path=temp_config)
    with pytest.raises(ValueError):
        config_manager.get_model_config("nonexistent_model")

def test_update_model_config(temp_config):
    """Test updating model configuration"""
    config_manager = ConfigManager(config_path=temp_config)
    updates = {"temp": 0.8, "max_tokens": 1000}
    config_manager.update_model_config("mistral", updates)
    
    # Verify updates
    model_config = config_manager.get_model_config("mistral")
    assert model_config.temp == 0.8
    assert model_config.max_tokens == 1000

def test_invalid_config_values(temp_config):
    """Test validation of config values"""
    config_manager = ConfigManager(config_path=temp_config)
    
    # Test invalid temperature
    with pytest.raises(ValueError):
        config_manager.update_model_config("mistral", {"temp": 2.0})
    
    # Test invalid port
    with pytest.raises(ValueError):
        config_manager.save_user_config({"ports": {"api": 70000}})

def test_user_config_persistence(temp_config):
    """Test that user configuration is properly saved and loaded"""
    config_manager = ConfigManager(config_path=temp_config)
    
    # Update configuration
    updates = {
        "paths": {
            "ollama": "/custom/path/to/ollama"
        }
    }
    config_manager.save_user_config(updates)
    
    # Create new instance to test loading
    new_config_manager = ConfigManager(config_path=temp_config)
    assert new_config_manager.config.paths.ollama == "/custom/path/to/ollama" 