"""Main launcher for Local LLM Chat Interface."""

import os
import sys
import asyncio
import logging
from pathlib import Path
import signal
import traceback
import platform

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
        
        # Initialize the orchestrator
        orchestrator = SystemOrchestrator(project_root=project_root)
        
        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Define shutdown event
        shutdown_event = asyncio.Event()
        
        def handle_shutdown():
            logger.info("Received shutdown signal")
            shutdown_event.set()
        
        # Set up platform-specific signal handling
        if platform.system() == "Windows":
            try:
                import win32api
                def windows_handler(type):
                    handle_shutdown()
                    return True
                win32api.SetConsoleCtrlHandler(windows_handler, True)
            except ImportError:
                # Fallback to basic handling on Windows if pywin32 is not available
                import signal
                signal.signal(signal.SIGINT, lambda x, y: handle_shutdown())
                signal.signal(signal.SIGTERM, lambda x, y: handle_shutdown())
        else:
            # Unix-like systems can use loop.add_signal_handler
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, handle_shutdown)
        
        try:
            # Run the orchestrator
            if not loop.run_until_complete(orchestrator.initialize()):
                logger.error("System initialization failed")
                sys.exit(1)
            
            # Wait for shutdown signal
            loop.run_until_complete(shutdown_event.wait())
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error during orchestrator execution: {e}")
            sys.exit(1)
        finally:
            # Run cleanup
            loop.run_until_complete(orchestrator.cleanup())
            
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for task cancellation
            if pending:
                loop.run_until_complete(asyncio.wait(pending, timeout=5.0))
            
            loop.close()
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 