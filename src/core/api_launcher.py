"""API Server launcher with proper process management."""

import uvicorn
import psutil
import signal
import sys
import os
import logging
import threading
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the FastAPI app
from src.core.api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / "logs" / "api_server.log")
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True

def kill_child_processes():
    """Kill all child processes of the current process."""
    try:
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                continue
            except Exception as e:
                logger.error(f"Error terminating child process {child.pid}: {e}")
        
        # Wait for processes to terminate and force kill if necessary
        _, alive = psutil.wait_procs(children, timeout=3)
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                continue
            except Exception as e:
                logger.error(f"Error killing child process {p.pid}: {e}")
                
    except Exception as e:
        logger.error(f"Error in kill_child_processes: {e}")

def cleanup():
    """Cleanup function to be called on exit."""
    global running
    running = False
    logger.info("Cleaning up API server processes...")
    kill_child_processes()

def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}. Shutting down API server...")
    cleanup()

def run_server():
    """Run the API server in a separate thread."""
    try:
        config = uvicorn.Config(
            app,
            host="localhost",
            port=8002,
            log_level="info",
            access_log=True,
            workers=1
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Error in run_server: {e}")
        cleanup()

def main():
    """Main function to run the API server."""
    global running
    
    try:
        # Create logs directory if it doesn't exist
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start server in a separate thread
        logger.info("Starting API server...")
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Keep the main thread alive
        while running and server_thread.is_alive():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        cleanup()
        logger.info("API server shutdown complete")

if __name__ == "__main__":
    main() 