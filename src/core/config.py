"""Configuration management for Local LLM Chat Interface."""

from pathlib import Path
import json
import os
from typing import Dict, Optional, Any
import logging
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    temp: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=500, gt=0)
    context_window: int = Field(default=4096, gt=0)

class HostConfig(BaseModel):
    ollama: str = Field(default="localhost")
    api: str = Field(default="localhost")
    streamlit: str = Field(default="localhost")

class PortConfig(BaseModel):
    ollama: int = Field(default=11434, gt=0, lt=65536)
    api: int = Field(default=8000, gt=0, lt=65536)
    streamlit: int = Field(default=8501, gt=0, lt=65536)

class PathConfig(BaseModel):
    ollama: Optional[str] = None
    models: str = Field(default="models")
    cache: str = Field(default="cache")
    logs: str = Field(default="logs")

class AppConfig(BaseModel):
    ports: PortConfig = Field(default_factory=PortConfig)
    hosts: HostConfig = Field(default_factory=HostConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    auto_open_browser: bool = True
    default_model: str = "mistral"
    log_level: str = Field(default="info", pattern="^(debug|info|warning|error|critical)$")

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.user_config_dir = Path.home() / ".local-llm"
        self.user_config_path = self.user_config_dir / "config.json"
        self.config = self.load_config()
        self.setup_logging()

    def load_config(self) -> AppConfig:
        """Load and merge configuration from default and user config files"""
        default_config = self._load_json(self.config_path, {})
        user_config = self._load_json(self.user_config_path, {})
        
        # Create default config if none exists
        if not default_config:
            default_config = AppConfig().model_dump()
            
        # Merge configurations
        merged_config = self._deep_merge(default_config, user_config)
        
        try:
            return AppConfig(**merged_config)
        except Exception as e:
            logging.error(f"Invalid configuration: {str(e)}")
            raise

    def _load_json(self, path: Path, default: Dict) -> Dict:
        """Load JSON file with fallback to default"""
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load config from {path}: {str(e)}")
            return default

    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save_user_config(self, updates: Dict[str, Any]) -> None:
        """Save user-specific configuration"""
        try:
            # Create user config directory if it doesn't exist
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Load existing user config or create new
            current_config = self._load_json(self.user_config_path, {})
            
            # Update configuration
            new_config = self._deep_merge(current_config, updates)
            
            # Validate by merging with default config
            default_config = AppConfig().model_dump()
            full_config = self._deep_merge(default_config, new_config)
            AppConfig(**full_config)
            
            # Save to file
            with open(self.user_config_path, 'w') as f:
                json.dump(new_config, f, indent=4)
                
            # Reload configuration
            self.config = self.load_config()
            
        except Exception as e:
            logging.error(f"Failed to save user configuration: {str(e)}")
            raise

    def setup_logging(self) -> None:
        """Configure logging based on settings"""
        log_levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        
        log_dir = Path(self.config.paths.logs)
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=log_levels[self.config.log_level],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "app.log"),
                logging.StreamHandler()
            ]
        )

    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a specific model"""
        if model_name not in self.config.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        return self.config.models[model_name]

    def update_model_config(self, model_name: str, updates: Dict[str, Any]) -> None:
        """Update configuration for a specific model"""
        if model_name not in self.config.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        
        current_config = self.config.models[model_name].model_dump()
        updated_config = self._deep_merge(current_config, updates)
        
        # Validate updates
        ModelConfig(**updated_config)
        
        # Save to user config
        self.save_user_config({
            "models": {
                model_name: updated_config
            }
        }) 