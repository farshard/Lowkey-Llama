"""Core launcher for Local LLM Chat Interface."""

import os
import sys
import json
import signal
import logging
import asyncio
import platform
from pathlib import Path
from typing import Dict, Optional
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from .api import APIServer
from .ui import UIServer
from .ollama import OllamaClient
from .dependencies import DependencyManager

logger = logging.getLogger(__name__)

class SystemInit:
    """System initialization for Local LLM Chat Interface."""
    
    def __init__(self):
        """Initialize system."""
        self.project_root = Path(__file__).parent.parent.parent
        self.config: Dict = {}
        self.api_server: Optional[APIServer] = None
        self.ui_server: Optional[UIServer] = None
        self.ollama: Optional[OllamaClient] = None
        self.dependency_manager = DependencyManager(self.project_root)
        self.progress: Optional[Progress] = None
        
    def _setup_logging(self):
        """Set up logging configuration."""
        # Create logs directory if it doesn't exist
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(logs_dir / "local_llm.log")
            ]
        )
        
        # Log system information
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Project root: {self.project_root}")
        
    def _setup_progress(self):
        """Set up progress tracking."""
        if not self.progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                transient=True
            )
            self.progress.start()
            
    def _cleanup_progress(self):
        """Clean up progress tracking."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        config_path = self.project_root / "config.json"
        if not config_path.exists():
            logger.warning("No config.json found, using defaults")
            return {}
            
        try:
            with open(config_path) as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
            
    async def _track(self, description: str, func, *args, **kwargs):
        """Track progress of an async function."""
        self._setup_progress()
        task = self.progress.add_task(description, total=None)
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self.progress.update(task, completed=True)
            return result
        except Exception as e:
            self.progress.update(task, completed=True)
            logger.error(f"{description} failed: {e}")
            raise
                
    async def check_ports(self) -> bool:
        """Check if required ports are available."""
        import psutil
        
        required_ports = {
            "API": self.config.get("ports", {}).get("api", 8000),
            "UI": self.config.get("ports", {}).get("ui", 8501),
            "Ollama": self.config.get("ports", {}).get("ollama", 11434)
        }
        
        for name, port in required_ports.items():
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    logger.error(f"Port {port} ({name}) is already in use")
                    return False
                    
        return True
        
    async def ensure_ollama(self) -> bool:
        """Ensure Ollama is installed and running."""
        host = self.config.get("hosts", {}).get("ollama", "localhost")
        port = self.config.get("ports", {}).get("ollama", 11434)
        
        self.ollama = OllamaClient(host=host, port=port)
        
        # Check if Ollama is running
        is_healthy = await self.ollama.health_check()
        if not is_healthy:
            logger.error("Ollama is not running")
            logger.error("\nPlease ensure Ollama is installed and running:")
            logger.error("1. Install Ollama from https://ollama.ai/download")
            if platform.system() == "Windows":
                logger.error("2. Open a new terminal and run: ollama serve")
            elif platform.system() == "Darwin":  # macOS
                logger.error("2. Run: brew services start ollama")
            else:  # Linux
                logger.error("2. Run: systemctl --user start ollama")
            logger.error("\nAfter starting Ollama, try running this application again.")
            return False
            
        # Check if any models are available
        models = await self.ollama.list_models()
        if not models:
            logger.warning("No models available in Ollama")
            default_model = self.config.get("models", {}).get("default")
            if default_model:
                logger.info(f"Pulling default model: {default_model}")
                try:
                    async for progress in self.ollama.pull_model(default_model):
                        logger.info(f"Pulling {default_model}: {progress['completed']}/{progress['total']} MB")
                except Exception as e:
                    logger.error(f"Failed to pull model {default_model}: {e}")
                    logger.error("\nPlease pull the model manually:")
                    logger.error(f"1. Open a new terminal")
                    logger.error(f"2. Run: ollama pull {default_model}")
                    logger.error("\nAfter pulling the model, try running this application again.")
                    return False
                    
        return True
        
    async def check_system_requirements(self) -> bool:
        """Check system requirements."""
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                logger.error("Python 3.8 or higher is required")
                return False
                
            # Check platform
            if platform.system() not in ["Linux", "Darwin", "Windows"]:
                logger.error("Unsupported platform")
                return False
                
            # Check dependencies
            if not await self._track(
                "Checking dependencies...",
                self.dependency_manager.ensure_dependencies
            ):
                return False
                
            # Check ports
            if not await self._track(
                "Checking ports...",
                self.check_ports
            ):
                return False
                
            # Check Ollama
            if not await self._track(
                "Checking Ollama...",
                self.ensure_ollama
            ):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"System requirements check failed: {e}")
            return False
            
    async def run_initialization(self):
        """Run system initialization."""
        try:
            # Set up logging
            self._setup_logging()
            
            # Load config
            self.config = await self._track(
                "Loading configuration...",
                self._load_config
            )
            
            # Check system requirements
            if not await self._track(
                "Checking system requirements...",
                self.check_system_requirements
            ):
                raise Exception("System requirements not met")
                
            # Initialize servers
            api_host = self.config.get("hosts", {}).get("api", "localhost")
            api_port = self.config.get("ports", {}).get("api", 8000)
            self.api_server = APIServer(host=api_host, port=api_port)
            
            ui_host = self.config.get("hosts", {}).get("ui", "localhost")
            ui_port = self.config.get("ports", {}).get("ui", 8501)
            self.ui_server = UIServer(api_host=api_host, api_port=api_port)
            
            # Start servers
            api_task = asyncio.create_task(
                self._track(
                    "Starting API server...",
                    self.api_server.start
                )
            )
            
            ui_task = asyncio.create_task(
                self._track(
                    "Starting UI server...",
                    self.ui_server.start
                )
            )
            
            # Wait for servers to start
            await asyncio.gather(api_task, ui_task)
            
            # Clean up progress tracking
            self._cleanup_progress()
            
            # Open browser if configured
            if self.config.get("auto_open_browser", True):
                import webbrowser
                webbrowser.open(f"http://{ui_host}:{ui_port}")
                
            logger.info(f"API server running at: http://{api_host}:{api_port}")
            logger.info(f"Web UI available at: http://{ui_host}:{ui_port}")
            logger.info("Initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self._cleanup_progress()
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.api_server:
                await self.api_server.stop()
                
            if self.ui_server:
                await self.ui_server.stop()
                
            if self.ollama:
                await self.ollama.close()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            
def main():
    """Main entry point."""
    # Set up signal handlers
    if platform.system() != "Windows":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(cleanup(s)))
            
    # Run initialization
    try:
        system = SystemInit()
        asyncio.run(system.run_initialization())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)
        
async def cleanup(sig):
    """Clean up on signal."""
    logger.info(f"Received signal {sig.name}, shutting down...")
    try:
        system = SystemInit()
        await system.cleanup()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
    finally:
        asyncio.get_event_loop().stop()
        
if __name__ == "__main__":
    main() 