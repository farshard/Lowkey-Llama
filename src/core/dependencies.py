"""Dependency management for Local LLM Chat Interface."""

import os
import sys
import venv
import logging
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pkg_resources
from pkg_resources import working_set

logger = logging.getLogger(__name__)

class DependencyManager:
    """Manages Python dependencies and virtual environment."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.venv_path = project_root / "venv"
        self.requirements_path = project_root / "requirements.txt"
        self._pip_path: Optional[str] = None
        self._python_path: Optional[str] = None
        
    @property
    def pip_path(self) -> str:
        """Get path to pip executable in virtual environment."""
        if not self._pip_path:
            if platform.system() == "Windows":
                self._pip_path = str(self.venv_path / "Scripts" / "pip.exe")
            else:
                self._pip_path = str(self.venv_path / "bin" / "pip")
        return self._pip_path
        
    @property
    def python_path(self) -> str:
        """Get path to Python executable in virtual environment."""
        if not self._python_path:
            if platform.system() == "Windows":
                self._python_path = str(self.venv_path / "Scripts" / "python.exe")
            else:
                self._python_path = str(self.venv_path / "bin" / "python")
        return self._python_path
        
    def is_venv_active(self) -> bool:
        """Check if running in a virtual environment."""
        return hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
    def create_venv(self) -> bool:
        """Create a new virtual environment if one doesn't exist."""
        try:
            if not self.venv_path.exists():
                logger.info("Creating virtual environment...")
                venv.create(self.venv_path, with_pip=True, clear=True)
                
                # Wait for venv creation
                for _ in range(10):  # 10 second timeout
                    if os.path.exists(self.pip_path):
                        break
                    import time
                    time.sleep(1)
                else:
                    logger.error("Timeout waiting for virtual environment creation")
                    return False
                
                # Upgrade pip in the new environment
                if not self._run_pip_command(["install", "--upgrade", "pip"]):
                    logger.error("Failed to upgrade pip")
                    return False
                    
                # Install wheel to avoid build issues
                if not self._run_pip_command(["install", "wheel"]):
                    logger.error("Failed to install wheel")
                    return False
                    
                logger.info("Virtual environment created successfully")
                return True
                
            logger.info("Using existing virtual environment")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            return False
            
    def get_installed_packages(self) -> Dict[str, str]:
        """Get dictionary of installed packages and their versions."""
        try:
            # Use pip list to get installed packages
            result = subprocess.run(
                [self.pip_path, "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            import json
            packages = json.loads(result.stdout)
            return {pkg["name"].lower(): pkg["version"] for pkg in packages}
        except Exception as e:
            logger.error(f"Failed to get installed packages: {e}")
            return {}
            
    def parse_requirements(self) -> List[Tuple[str, Optional[str]]]:
        """Parse requirements.txt into list of (package, version) tuples."""
        requirements = []
        try:
            with open(self.requirements_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('--'):
                        continue
                        
                    # Handle platform-specific requirements
                    if ';' in line:
                        pkg_spec, condition = line.split(';', 1)
                        # Skip if condition doesn't match current platform
                        if not self._evaluate_marker(condition.strip()):
                            continue
                        line = pkg_spec.strip()
                        
                    # Parse package name and version
                    if '>=' in line:
                        name, version = line.split('>=', 1)
                        version = version.split(',')[0]  # Take minimum version
                    elif '==' in line:
                        name, version = line.split('==', 1)
                    else:
                        name, version = line, None
                        
                    requirements.append((name.strip().lower(), version.strip() if version else None))
                    
        except FileNotFoundError:
            logger.error("requirements.txt not found")
        except Exception as e:
            logger.error(f"Error parsing requirements.txt: {e}")
            
        return requirements
        
    def _evaluate_marker(self, marker: str) -> bool:
        """Evaluate a PEP 508 environment marker."""
        try:
            import platform
            namespace = {
                'platform_system': platform.system(),
                'platform_machine': platform.machine(),
                'sys_platform': sys.platform,
            }
            return eval(marker, {'__builtins__': {}}, namespace)
        except Exception:
            return True  # If we can't evaluate, assume it's needed
            
    def check_dependencies(self) -> Tuple[List[str], List[str]]:
        """Check installed dependencies against requirements."""
        installed = self.get_installed_packages()
        required = self.parse_requirements()
        
        missing = []
        outdated = []
        
        for package, version in required:
            if package not in installed:
                missing.append(package)
            elif version and installed[package] != version:
                try:
                    from packaging.version import parse
                    if parse(installed[package]) < parse(version):
                        outdated.append(package)
                except Exception:
                    # If version comparison fails, assume it needs updating
                    outdated.append(package)
                    
        return missing, outdated
        
    def _run_pip_command(self, args: List[str], capture_output: bool = True) -> bool:
        """Run a pip command in the virtual environment."""
        try:
            cmd = [self.pip_path] + args
            logger.debug(f"Running pip command: {' '.join(cmd)}")
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)
            
            if capture_output:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False  # Don't raise on non-zero exit
                )
                if result.returncode != 0:
                    logger.error(f"Pip command failed with output:\n{result.stderr}")
                return result.returncode == 0
            else:
                # Show progress for installations
                subprocess.run(cmd, env=env, check=True)
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Pip command failed: {e}")
            if e.stderr:
                logger.error(f"Error output:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error running pip command: {e}")
            return False
            
    def install_dependencies(self, missing: List[str], outdated: List[str]) -> bool:
        """Install missing and update outdated packages."""
        if not missing and not outdated:
            return True
            
        try:
            if missing:
                logger.info(f"Installing missing packages: {', '.join(missing)}")
                if not self._run_pip_command(
                    ["install", "-r", str(self.requirements_path)],
                    capture_output=False
                ):
                    return False
                    
            if outdated:
                logger.info(f"Updating outdated packages: {', '.join(outdated)}")
                if not self._run_pip_command(
                    ["install", "--upgrade", "-r", str(self.requirements_path)],
                    capture_output=False
                ):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
            
    def ensure_dependencies(self) -> bool:
        """Ensure all dependencies are installed and up to date."""
        if not self.is_venv_active():
            logger.info("Not running in a virtual environment")
            if not self.create_venv():
                return False
                
        missing, outdated = self.check_dependencies()
        if missing or outdated:
            return self.install_dependencies(missing, outdated)
            
        logger.info("All dependencies are up to date")
        return True 