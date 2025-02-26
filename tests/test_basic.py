"""Basic tests to verify project setup."""

import pytest
from pathlib import Path

def test_project_structure():
    """Test that required project directories and files exist."""
    project_root = Path(__file__).parent.parent
    
    # Check core directories
    assert (project_root / "src").is_dir()
    assert (project_root / "src" / "core").is_dir()
    assert (project_root / "src" / "api").is_dir()
    assert (project_root / "src" / "ui").is_dir()
    
    # Check core files
    assert (project_root / "src" / "__init__.py").is_file()
    assert (project_root / "config.json").is_file()
    assert (project_root / "requirements.txt").is_file()
    
    # Check application files
    assert (project_root / "src" / "api" / "server.py").is_file()
    assert (project_root / "src" / "ui" / "app.py").is_file()
    assert (project_root / "src" / "core" / "launcher.py").is_file()

def test_config_exists():
    """Test that config.json exists and is valid JSON."""
    import json
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config.json"
    
    assert config_path.exists()
    with open(config_path) as f:
        config = json.load(f)
    
    # Check required config sections
    assert "ports" in config
    assert "hosts" in config
    assert "models" in config 