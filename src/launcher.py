"""Main application launcher."""

import subprocess
import sys
import os
import time
import signal
import psutil
import logging
import requests
import socket
from pathlib import Path

# Global process handles
api_process = None
streamlit_process = None

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / "logs" / "launcher.log")
    ]
)
logger = logging.getLogger(__name__)

def kill_process_tree(pid):
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        try:
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

def cleanup_processes():
    """Clean up any running processes"""
    global api_process, streamlit_process
    try:
        # Get list of processes to clean up
        processes = []
        if api_process and api_process.poll() is None:
            processes.append(api_process.pid)
        if streamlit_process and streamlit_process.poll() is None:
            processes.append(streamlit_process.pid)
            
        # Kill each process tree
        for pid in processes:
            kill_process_tree(pid)
            
        # Clear process references
        api_process = None 
        streamlit_process = None
        
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    cleanup_processes()
    sys.exit(0)

def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def wait_for_api(timeout=30, interval=0.5):
    """Wait for API server to be ready."""
    start_time = time.time()
    last_log_time = 0  # To prevent log spam
    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://localhost:8002/health", timeout=5)  # Increased timeout
            if response.status_code == 200:
                # Only log if we haven't logged in the last 5 seconds
                current_time = time.time()
                if current_time - last_log_time > 5:
                    logger.info("API server is ready")
                    last_log_time = current_time
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.debug(f"API not ready yet: {e}")
            pass
        except Exception as e:
            logger.warning(f"Unexpected error checking API: {e}")
        time.sleep(interval)
    return False

def wait_for_streamlit(port, timeout=30, interval=0.5):
    """Wait for Streamlit server to be ready."""
    start_time = time.time()
    last_log_time = 0
    while time.time() - start_time < timeout:
        try:
            # First check basic port connectivity
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    # Port is open, now check if Streamlit is responding
                    try:
                        # Try multiple endpoints that Streamlit might respond to
                        endpoints = ['healthz', '_stcore/health', '']
                        for endpoint in endpoints:
                            try:
                                url = f"http://localhost:{port}/{endpoint}"
                                response = requests.get(url, timeout=2)
                                if response.status_code in [200, 404]:  # 404 is ok, means Streamlit is running
                                    current_time = time.time()
                                    if current_time - last_log_time > 5:
                                        logger.info("Streamlit server is ready")
                                        last_log_time = current_time
                                    return True
                            except requests.RequestException:
                                continue
                    except Exception as e:
                        logger.debug(f"Streamlit health check error: {e}")
        except Exception as e:
            logger.debug(f"Socket connection error: {e}")
        time.sleep(interval)
    return False

def kill_process_on_port(port):
    """Kill process using specified port."""
    try:
        # For Windows, try multiple approaches
        success = False
        
        # Approach 1: Using netstat
        cmd = f'netstat -ano | findstr :{port}'
        try:
            output = subprocess.check_output(cmd, shell=True).decode()
            if output:
                for line in output.split('\n'):
                    if f':{port}' in line:
                        pid = line.strip().split()[-1]
                        try:
                            kill_process_tree(int(pid))
                            success = True
                        except Exception as e:
                            logger.error(f"Failed to kill process {pid} using netstat approach: {e}")
        except Exception as e:
            logger.error(f"Netstat approach failed: {e}")

        # Approach 2: Using taskkill directly on the port
        if not success:
            try:
                subprocess.run(f'taskkill /F /FI "PID ne 0" /FI "LOCALPORT eq {port}"', shell=True)
                success = True
            except Exception as e:
                logger.error(f"Taskkill approach failed: {e}")

        # Approach 3: Force TCP port release
        try:
            subprocess.run(f'netsh int ipv4 delete excludedportrange protocol=tcp startport={port} numberofports=1', shell=True)
            subprocess.run(f'netsh int ipv4 add excludedportrange protocol=tcp startport={port} numberofports=1', shell=True)
        except Exception as e:
            logger.error(f"Port exclusion approach failed: {e}")

        # Verify port is actually free
        max_retries = 5
        retry_delay = 1
        for attempt in range(max_retries):
            if not is_port_in_use(port):
                logger.info(f"Port {port} successfully freed")
                return True
            if attempt < max_retries - 1:
                logger.warning(f"Port {port} still in use, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                
        if is_port_in_use(port):
            logger.error(f"Failed to free port {port} after all attempts")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error in kill_process_on_port: {e}")
        return False

def open_browser(url, delay=1.5):
    """Open browser with delay to ensure server is ready."""
    import webbrowser
    import threading
    threading.Timer(delay, lambda: webbrowser.open(url)).start()

def main():
    """Main function to launch the application."""
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Store processes for cleanup
    processes = []
    signal_handler.processes = processes
    
    # Set up environment with improved error handling
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    env["STREAMLIT_SERVER_MAX_RETRIES"] = "3"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_ADDRESS"] = "localhost"
    
    try:
        # First check if API server is already running
        logger.info("Checking for existing API server...")
        api_process = None
        api_ready = wait_for_api(timeout=10)
        
        if not api_ready:
            # Start API server using the new launcher
            logger.info("Starting new API server...")
            
            # Platform-specific process creation flags
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            
            api_process = subprocess.Popen([
                sys.executable,
                str(project_root / "src" / "core" / "api_launcher.py")
            ], env=env, creationflags=creation_flags,
               start_new_session=sys.platform != "win32")
            processes.append(api_process)
            
            # Wait for API server with increased timeout and better logging
            start_time = time.time()
            api_ready = False
            while time.time() - start_time < 45:  # 45 second timeout
                if wait_for_api(timeout=5):
                    api_ready = True
                    break
                if api_process.poll() is not None:
                    logger.error(f"API server process terminated with exit code {api_process.poll()}")
                    break
                logger.info("Waiting for API server to be ready...")
                time.sleep(2)
                
            if not api_ready:
                logger.error("API server failed to start within timeout")
                cleanup_processes()
                return

        # Check and cleanup Streamlit port with improved error handling
        streamlit_port = 8501
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            if not is_port_in_use(streamlit_port):
                break
                
            logger.info(f"Port {streamlit_port} is in use, attempting to free it (attempt {attempt + 1}/{max_retries})...")
            if kill_process_on_port(streamlit_port):
                # Wait to ensure port is fully released
                time.sleep(retry_delay)
                if not is_port_in_use(streamlit_port):
                    logger.info(f"Successfully freed port {streamlit_port}")
                    break
            
            if attempt == max_retries - 1:
                logger.error(f"Failed to free port {streamlit_port} after {max_retries} attempts")
                cleanup_processes()
                return
        
        # Start Streamlit UI with improved process management
        logger.info("Starting Streamlit UI...")
        
        # Create unique config directory
        config_dir = project_root / "temp" / f"streamlit_{os.getpid()}"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced Streamlit environment variables
        env.update({
            'STREAMLIT_SERVER_PORT': str(streamlit_port),
            'STREAMLIT_SERVER_HEADLESS': 'true',
            'STREAMLIT_SERVER_FILE_WATCHER_TYPE': 'none',
            'STREAMLIT_CONFIG_DIR': str(config_dir),
            'STREAMLIT_THEME_BASE': 'dark',
            'STREAMLIT_SERVER_RUN_ON_SAVE': 'false',
            'STREAMLIT_SERVER_ENABLE_CORS': 'false',
            'STREAMLIT_LOGGER_LEVEL': 'error',
            'STREAMLIT_CLIENT_TOOLBAR_MODE': 'minimal',
            'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false',
            'STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION': 'false',
            'STREAMLIT_BROWSER_SERVER_ADDRESS': 'localhost',
            'STREAMLIT_SERVER_MAX_UPLOAD_SIZE': '100'
        })
        
        # Platform-specific process creation flags
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        
        ui_process = subprocess.Popen([
            sys.executable,
            "-m", "streamlit",
            "run",
            str(project_root / "src" / "ui" / "app.py"),
            "--server.port", str(streamlit_port),
            "--server.address", "localhost",
            "--server.headless", "true",
            "--server.runOnSave", "false",
            "--server.maxUploadSize", "100",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--server.fileWatcherType", "none",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "dark",
            "--logger.level", "error",
            "--client.showErrorDetails", "false",
            "--client.toolbarMode", "minimal",
            "--server.enableWebsocketCompression", "false"
        ], env=env, creationflags=creation_flags,
           start_new_session=sys.platform != "win32")
        processes.append(ui_process)
        
        # Wait for Streamlit with improved error handling
        start_time = time.time()
        ui_ready = False
        while time.time() - start_time < 45:  # 45 second timeout
            if wait_for_streamlit(streamlit_port, timeout=5):
                ui_ready = True
                break
            if ui_process.poll() is not None:
                logger.error(f"UI process terminated with exit code {ui_process.poll()}")
                break
            logger.info("Waiting for Streamlit server to be ready...")
            time.sleep(2)
            
        if not ui_ready:
            logger.error("Streamlit server failed to start within timeout")
            cleanup_processes()
            return
            
        logger.info("Application started successfully")
        
        # Open browser after ensuring everything is ready
        streamlit_url = f"http://localhost:{streamlit_port}"
        open_browser(streamlit_url, delay=2)
        logger.info(f"Opening browser to {streamlit_url}")
        
        # Monitor processes with improved error handling
        last_log_time = 0
        log_interval = 30  # Log health status every 30 seconds
        
        while True:
            # Check API process if we started it
            if api_process and api_process.poll() is not None:
                exit_code = api_process.poll()
                logger.error(f"API server process terminated unexpectedly with exit code {exit_code}")
                break
                
            # Check UI process
            if ui_process.poll() is not None:
                exit_code = ui_process.poll()
                logger.error(f"UI process terminated unexpectedly with exit code {exit_code}")
                break
                
            # Verify services are still responsive
            if not wait_for_api(timeout=2) or not wait_for_streamlit(streamlit_port, timeout=2):
                logger.error("One or more services are not responding. Attempting cleanup...")
                cleanup_processes()
                break
                
            current_time = time.time()
            if current_time - last_log_time >= log_interval:
                logger.info("API server is ready")
                logger.info("Streamlit server is ready")
                last_log_time = current_time
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error running application: {e}")
        logger.exception("Full traceback:")
    finally:
        logger.info("Cleaning up...")
        cleanup_processes()
        try:
            if 'config_dir' in locals():
                import shutil
                shutil.rmtree(config_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Error cleaning up config directory: {e}")
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main() 