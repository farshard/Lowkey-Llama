"""Tests for dependency management system."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.dependencies import DependencyManager

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory with requirements.txt."""
    requirements = """
    aiohttp==3.8.1
    fastapi==0.68.0
    streamlit==1.2.0
    # Comment line
    rich>=10.0.0
    """
    
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "requirements.txt").write_text(requirements.strip())
    return project_dir

@pytest.fixture
def dep_manager(temp_project):
    """Create a DependencyManager instance with a temporary project."""
    return DependencyManager(temp_project)

def test_init(dep_manager, temp_project):
    """Test initialization of DependencyManager."""
    assert dep_manager.project_root == temp_project
    assert dep_manager.venv_path == temp_project / "venv"
    assert dep_manager.requirements_path == temp_project / "requirements.txt"

def test_pip_path(dep_manager):
    """Test pip path property."""
    if sys.platform == "win32":
        expected = str(dep_manager.venv_path / "Scripts" / "pip.exe")
    else:
        expected = str(dep_manager.venv_path / "bin" / "pip")
    assert dep_manager.pip_path == expected

def test_is_venv_active(dep_manager):
    """Test virtual environment detection."""
    with patch.object(sys, 'prefix', 'venv'):
        with patch.object(sys, 'base_prefix', 'base'):
            assert dep_manager.is_venv_active() is True
            
    with patch.object(sys, 'prefix', 'base'):
        with patch.object(sys, 'base_prefix', 'base'):
            assert dep_manager.is_venv_active() is False

def test_parse_requirements(dep_manager):
    """Test requirements.txt parsing."""
    requirements = dep_manager.parse_requirements()
    assert ('aiohttp', '3.8.1') in requirements
    assert ('fastapi', '0.68.0') in requirements
    assert ('streamlit', '1.2.0') in requirements
    assert ('rich', None) in requirements  # Version with >= is treated as unversioned

def test_check_dependencies(dep_manager):
    """Test dependency checking."""
    installed = {
        'aiohttp': '3.8.1',
        'fastapi': '0.68.0',
        'streamlit': '1.1.0',  # Outdated
        'pytest': '6.0.0'  # Extra package
    }
    
    with patch.object(dep_manager, 'get_installed_packages', return_value=installed):
        missing, outdated = dep_manager.check_dependencies()
        assert 'rich' in missing  # Not installed
        assert 'streamlit' in outdated  # Wrong version

@pytest.mark.asyncio
async def test_create_venv(dep_manager):
    """Test virtual environment creation."""
    with patch('venv.create') as mock_create:
        with patch.object(dep_manager, '_run_pip_command', return_value=True):
            assert dep_manager.create_venv() is True
            mock_create.assert_called_once_with(dep_manager.venv_path, with_pip=True)

def test_install_dependencies(dep_manager):
    """Test dependency installation."""
    missing = ['package1', 'package2']
    outdated = ['package3']
    
    with patch.object(dep_manager, '_run_pip_command', return_value=True) as mock_pip:
        assert dep_manager.install_dependencies(missing, outdated) is True
        assert mock_pip.call_count == 2
        
        # Check install command for missing packages
        install_call = mock_pip.call_args_list[0]
        assert install_call[0][0] == ['install'] + missing
        
        # Check upgrade command for outdated packages
        upgrade_call = mock_pip.call_args_list[1]
        assert upgrade_call[0][0] == ['install', '--upgrade'] + outdated

def test_ensure_dependencies_no_venv(dep_manager):
    """Test dependency ensuring when not in a virtual environment."""
    with patch.object(dep_manager, 'is_venv_active', return_value=False):
        with patch.object(dep_manager, 'create_venv', return_value=False):
            assert dep_manager.ensure_dependencies() is False

def test_ensure_dependencies_with_updates(dep_manager):
    """Test dependency ensuring with updates needed."""
    with patch.object(dep_manager, 'is_venv_active', return_value=True):
        with patch.object(dep_manager, 'check_dependencies', return_value=(['pkg1'], ['pkg2'])):
            with patch.object(dep_manager, 'install_dependencies', return_value=True):
                assert dep_manager.ensure_dependencies() is True

def test_ensure_dependencies_all_good(dep_manager):
    """Test dependency ensuring when everything is up to date."""
    with patch.object(dep_manager, 'is_venv_active', return_value=True):
        with patch.object(dep_manager, 'check_dependencies', return_value=([], [])):
            assert dep_manager.ensure_dependencies() is True

def test_run_pip_command_success(dep_manager):
    """Test successful pip command execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert dep_manager._run_pip_command(['install', 'package']) is True
        mock_run.assert_called_once()

def test_run_pip_command_failure(dep_manager):
    """Test failed pip command execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Pip error")
        assert dep_manager._run_pip_command(['install', 'package']) is False 