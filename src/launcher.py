"""Main launcher for Local LLM Chat Interface."""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Create logs directory
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure basic logging until core takes over
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(logs_dir / "local_llm.log")
    ]
)

logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version meets requirements."""
    if sys.version_info < (3, 8):
        logger.error(f"Python 3.8+ required (found {platform.python_version()})")
        return False
    return True

def check_platform():
    """Check if platform is supported."""
    if platform.system() not in ["Linux", "Darwin", "Windows"]:
        logger.error(f"Unsupported platform: {platform.system()}")
        return False
    return True

def activate_venv():
    """Activate virtual environment."""
    venv_path = project_root / "venv"
    if not venv_path.exists():
        logger.info("Creating virtual environment...")
        import venv
        venv.create(venv_path, with_pip=True)
        
    if platform.system() == "Windows":
        python_path = venv_path / "Scripts" / "python.exe"
        if not python_path.exists():
            logger.error("Virtual environment Python not found")
            return False
            
        # Re-run the script with the virtual environment Python
        if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
            logger.info("Activating virtual environment...")
            os.execv(str(python_path), [str(python_path), __file__])
    else:
        activate_script = venv_path / "bin" / "activate"
        if not activate_script.exists():
            logger.error("Virtual environment activation script not found")
            return False
            
        # Source the activation script
        if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
            logger.info("Activating virtual environment...")
            activate_cmd = f"source {activate_script} && exec {sys.executable} {__file__}"
            os.execv("/bin/bash", ["/bin/bash", "-c", activate_cmd])
            
    return True

def main():
    """Main entry point for the application."""
    try:
        # Import here after path setup
        from core.orchestrator import SystemOrchestrator
        
        # Initialize and start the system
        orchestrator = SystemOrchestrator(project_root=project_root)
        asyncio.run(orchestrator.initialize())
        
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        asyncio.run(orchestrator.cleanup())
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 