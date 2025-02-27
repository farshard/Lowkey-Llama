"""Ollama server manager for Lowkey Llama."""

import os
import sys
import time
import signal
import logging
import platform
import subprocess
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ollama_server.log')
    ]
)

logger = logging.getLogger(__name__)

class OllamaServer:
    """Manages the Ollama server process."""
    
    def __init__(self):
        """Initialize the Ollama server manager."""
        self.process: Optional[subprocess.Popen] = None
        self.platform = platform.system()
        
    def _find_ollama_path(self) -> Optional[str]:
        """Find the Ollama executable path."""
        if self.platform == "Windows":
            # Check common Windows installation paths
            paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
                r"C:\Program Files\Ollama\ollama.exe",
                r"C:\Program Files (x86)\Ollama\ollama.exe"
            ]
        else:
            # Check common Unix paths
            paths = [
                "/usr/local/bin/ollama",
                "/usr/bin/ollama",
                "/opt/homebrew/bin/ollama"  # macOS Homebrew path
            ]
            
        for path in paths:
            if os.path.isfile(path):
                return path
                
        # Try finding in PATH
        try:
            if self.platform == "Windows":
                result = subprocess.run(["where", "ollama"], capture_output=True, text=True)
            else:
                result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
                
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
            
        return None
        
    def start(self) -> bool:
        """Start the Ollama server.
        
        Returns:
            bool: True if server started successfully, False otherwise
        """
        try:
            # Find Ollama executable
            ollama_path = self._find_ollama_path()
            if not ollama_path:
                logger.error("Ollama executable not found. Please install Ollama from https://ollama.ai/download")
                return False
                
            logger.info(f"Found Ollama at: {ollama_path}")
            
            # Start Ollama server
            cmd = [ollama_path, "serve"]
            
            # Use CREATE_NEW_CONSOLE on Windows to keep server running in background
            if self.platform == "Windows":
                self.process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            # Wait for server to start
            time.sleep(2)
            
            # Check if process is still running
            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                logger.error(f"Failed to start Ollama server: {stderr.decode()}")
                return False
                
            logger.info("Ollama server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting Ollama server: {e}")
            return False
            
    def stop(self):
        """Stop the Ollama server."""
        if self.process:
            try:
                if self.platform == "Windows":
                    # On Windows, we need to terminate the process tree
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
                else:
                    # On Unix, we can just send SIGTERM
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    
                logger.info("Ollama server stopped")
            except Exception as e:
                logger.error(f"Error stopping Ollama server: {e}")
            finally:
                self.process = None
                
def main():
    """Main entry point."""
    server = OllamaServer()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signal.Signals(signum).name}")
        server.stop()
        sys.exit(0)
        
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if server.start():
            logger.info("Press Ctrl+C to stop the server")
            # Keep the main thread alive
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.stop()
        
if __name__ == "__main__":
    main() 