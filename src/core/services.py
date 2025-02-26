"""Service manager for Local LLM Chat Interface."""

import os
import sys
import signal
import psutil
import asyncio
import aiohttp # type: ignore
import logging
import socket
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import subprocess

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages services for the Local LLM Chat Interface."""
    
    OLLAMA_PATHS = [
        # Windows paths
        "C:\\Program Files\\Ollama\\ollama.exe",
        "C:\\Program Files (x86)\\Ollama\\ollama.exe",
        "C:\\Users\\{}\\AppData\\Local\\Programs\\Ollama\\ollama.exe",
        "C:\\Users\\{}\\AppData\\Local\\Ollama\\ollama.exe",
        # Unix-like paths
        "/usr/local/bin/ollama",
        "/opt/homebrew/bin/ollama",
        "/usr/bin/ollama",
        # Relative paths
        "ollama.exe",  # If in PATH (Windows)
        "ollama"  # If in PATH (Unix)
    ]
    
    def __init__(self, config_manager):
        """Initialize service manager."""
        self.config_manager = config_manager
        self.processes: Dict[str, psutil.Process] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._ollama_path: Optional[str] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        async with self._lock:
            if not self._session or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=30)
                self._session = aiohttp.ClientSession(timeout=timeout)
            return self._session
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
                
            # Stop all services
            await self.stop_all_services()
            
            # Kill any remaining Streamlit processes
            self.kill_streamlit_processes()
            
            # Clean up temporary files
            try:
                temp_dir = Path(__file__).parent.parent.parent / "temp"
                if temp_dir.exists():
                    for item in temp_dir.iterdir():
                        if item.is_dir() and item.name.startswith("streamlit_"):
                            try:
                                import shutil
                                shutil.rmtree(item)
                            except Exception as e:
                                logger.warning(f"Failed to remove temp directory {item}: {e}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            # Ensure session is closed even if other cleanup fails
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
        
    def validate_ollama_executable(self, path: str) -> Tuple[bool, Optional[str]]:
        """Validate if a path points to a valid Ollama executable.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            if not os.path.exists(path):
                return False, f"Path does not exist: {path}"
                
            if not os.path.isfile(path):
                return False, f"Path is not a file: {path}"
                
            # Check if it's executable
            if not os.access(path, os.X_OK):
                return False, f"File is not executable: {path}"
                
            # Try to run version check
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return False, f"Failed to run version check: {result.stderr}"
                    
                if "ollama" not in result.stdout.lower():
                    return False, "Not a valid Ollama executable"
                    
                return True, None
                
            except subprocess.TimeoutExpired:
                return False, "Version check timed out"
            except subprocess.SubprocessError as e:
                return False, f"Failed to run version check: {str(e)}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
            
    def find_ollama_path(self) -> Optional[str]:
        """Find the Ollama executable path."""
        if self._ollama_path:
            return self._ollama_path
            
        # First try the configured path
        configured_path = self.config_manager.config.paths.ollama
        if configured_path:
            is_valid, error = self.validate_ollama_executable(configured_path)
            if is_valid:
                self._ollama_path = str(configured_path)
                return self._ollama_path
            else:
                logger.warning(f"Configured Ollama path is invalid: {error}")
                
        # Try PATH first (most reliable)
        ollama_in_path = shutil.which("ollama")
        if ollama_in_path:
            is_valid, error = self.validate_ollama_executable(ollama_in_path)
            if is_valid:
                self._ollama_path = ollama_in_path
                self.config_manager.save_user_config({
                    "paths": {"ollama": str(ollama_in_path)}
                })
                logger.info(f"Found Ollama in PATH at {ollama_in_path}, updating config")
                return self._ollama_path
                
        # Try common paths
        username = os.getenv("USERNAME") or os.getenv("USER", "")
        for path_template in self.OLLAMA_PATHS:
            try:
                path = path_template.format(username)
                is_valid, error = self.validate_ollama_executable(path)
                if is_valid:
                    self._ollama_path = str(path)
                    self.config_manager.save_user_config({
                        "paths": {"ollama": str(path)}
                    })
                    logger.info(f"Found Ollama at {path}, updating config")
                    return self._ollama_path
            except Exception as e:
                logger.debug(f"Error checking path {path}: {e}")
                continue
                
        # If we get here, we couldn't find Ollama
        logger.error("Could not find Ollama executable in any standard location")
        return None
            
    def find_ollama_processes(self) -> Dict[str, List[psutil.Process]]:
        """Find all Ollama-related processes.
        
        Returns:
            Dict with keys 'server' and 'app' containing lists of processes
        """
        processes = {
            'server': [],  # ollama.exe processes
            'app': []      # ollama app.exe processes
        }
        
        try:
            for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
                try:
                    name = proc.info['name'].lower() if proc.info['name'] else ''
                    exe = proc.info['exe'].lower() if proc.info['exe'] else ''
                    cmdline = [cmd.lower() for cmd in proc.info['cmdline']] if proc.info['cmdline'] else []
                    
                    # Check for ollama app.exe (GUI application)
                    if 'ollama app' in name or 'ollama app.exe' in exe or any('ollama app' in cmd for cmd in cmdline):
                        processes['app'].append(proc)
                        continue
                        
                    # Check for ollama.exe (server)
                    if (name == 'ollama.exe' or name == 'ollama' or 
                        'ollama.exe' in exe or 
                        any(cmd == 'ollama' or cmd == 'ollama.exe' or cmd == 'serve' for cmd in cmdline)):
                        processes['server'].append(proc)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"Error finding Ollama processes: {e}")
            
        return processes
            
    def is_ollama_process_running(self) -> bool:
        """Check if any Ollama process is running."""
        processes = self.find_ollama_processes()
        return bool(processes['server'] or processes['app'])
            
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
            
    def kill_process_on_port(self, port: int, force: bool = False) -> bool:
        """Kill process using a specific port."""
        try:
            if sys.platform == 'win32':
                # On Windows, use netstat to find the process
                cmd = f'netstat -ano | findstr :{port}'
                output = subprocess.check_output(cmd, shell=True).decode()
                if output:
                    # Extract PID from the last line that has our port
                    for line in output.splitlines():
                        if f":{port}" in line:
                            try:
                                pid = int(line.strip().split()[-1])
                                process = psutil.Process(pid)
                                
                                # Log what we're killing
                                logger.info(f"Terminating process {pid} using port {port}")
                                
                                # Kill process tree for known services
                                if port in [8501]:  # Streamlit
                                    for child in process.children(recursive=True):
                                        try:
                                            child.kill()
                                        except psutil.NoSuchProcess:
                                            pass
                                    process.kill()
                                else:
                                    process.terminate()
                                    try:
                                        process.wait(timeout=5)
                                    except psutil.TimeoutExpired:
                                        if force:
                                            process.kill()
                                            process.wait(timeout=1)
                                return True
                            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                                continue
            else:
                # On Unix-like systems, use lsof
                cmd = f'lsof -ti:{port}'
                try:
                    output = subprocess.check_output(cmd, shell=True).decode()
                    if output:
                        pid = int(output.strip())
                        process = psutil.Process(pid)
                        
                        # Log what we're killing
                        logger.info(f"Terminating process {pid} using port {port}")
                        
                        if port in [8501]:  # Streamlit
                            for child in process.children(recursive=True):
                                try:
                                    child.kill()
                                except psutil.NoSuchProcess:
                                    pass
                            process.kill()
                        else:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except psutil.TimeoutExpired:
                                if force:
                                    process.kill()
                                    process.wait(timeout=1)
                        return True
                except (subprocess.CalledProcessError, ValueError, psutil.NoSuchProcess):
                    pass
        except Exception as e:
            logger.warning(f"Failed to kill process on port {port}: {e}")
        return False
            
    async def check_ollama_health(self, timeout: float = 5.0) -> bool:
        """Check if Ollama is healthy."""
        try:
            session = await self.get_session()
            
            # Try both /api/tags and /tags first since they're more reliable
            endpoints = ["/api/tags", "/tags"]
            for endpoint in endpoints:
                try:
                    async with session.get(
                        f"http://localhost:11434{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            return True
                except Exception:
                    continue
                    
            # Fallback to health endpoints
            endpoints = ["/api/health", "/health"]
            for endpoint in endpoints:
                try:
                    async with session.get(
                        f"http://localhost:11434{endpoint}",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            return True
                except Exception:
                    continue
                    
            return False
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False
            
    async def check_api_health(self, timeout: float = 5.0) -> bool:
        """Check if API is healthy."""
        try:
            session = await self.get_session()
            async with session.get(
                "http://localhost:8000/health",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False
            
    async def start_ollama(self) -> bool:
        """Start Ollama service."""
        # First check if Ollama is already running and healthy
        if await self.check_ollama_health(timeout=1.0):
            logger.info("Ollama is already running and healthy")
            return True
            
        # Check existing processes
        processes = self.find_ollama_processes()
        
        # If the app is running but service isn't healthy, wait for it
        if processes['app'] and self.is_port_in_use(11434):
            logger.info("Found Ollama app running, waiting for service to become healthy...")
            
            # Try to wait for service to become healthy
            for _ in range(30):  # 30 second timeout
                if await self.check_ollama_health(timeout=1.0):
                    logger.info("Ollama service is now healthy")
                    return True
                await asyncio.sleep(1)
                
            logger.warning("Ollama app is running but service is not becoming healthy")
            return False  # Don't try to start server if app is running
            
        # If server processes exist but aren't healthy
        if processes['server'] and self.is_port_in_use(11434):
            logger.info("Found existing Ollama server processes, attempting cleanup...")
            
            # Try to terminate server processes
            for proc in processes['server']:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                except psutil.NoSuchProcess:
                    pass
                    
            # Wait for port to be released
            for _ in range(10):  # 10 second timeout
                if not self.is_port_in_use(11434):
                    break
                await asyncio.sleep(1)
            else:
                logger.error("Port 11434 is still in use after terminating processes")
                return False
            
        # Try to find Ollama executable
        ollama_path = self.find_ollama_path()
        if not ollama_path:
            # Try common user-specific paths
            username = os.getenv("USERNAME") or os.getenv("USER", "")
            potential_paths = [
                f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Ollama\\ollama.exe",
                f"C:\\Users\\{username}\\AppData\\Local\\Ollama\\ollama.exe",
                "C:\\Program Files\\Ollama\\ollama.exe",
                "C:\\Program Files (x86)\\Ollama\\ollama.exe"
            ]
            
            for path in potential_paths:
                if Path(path).exists():
                    ollama_path = path
                    # Update config with found path
                    self.config_manager.save_user_config({
                        "paths": {"ollama": str(path)}
                    })
                    logger.info(f"Found Ollama at {path}, updating config")
                    break
                    
            if not ollama_path:
                logger.error("Could not find Ollama executable in any location")
                return False
            
        try:
            # Convert string path to Path object
            ollama_path = Path(ollama_path)
            logger.info(f"Starting Ollama from: {ollama_path}")
            
            # On Windows, check if we found ollama app.exe instead of ollama.exe
            if ollama_path.name.lower() == 'ollama app.exe':
                # Try to find ollama.exe in the same directory
                server_path = ollama_path.parent / 'ollama.exe'
                if server_path.exists():
                    ollama_path = server_path
                    logger.info(f"Found server executable at: {ollama_path}")
                else:
                    logger.error("Found Ollama app but could not find server executable")
                    return False
            
            # Ensure the path exists
            if not ollama_path.exists():
                logger.error(f"Ollama executable not found at {ollama_path}")
                return False
                
            # Start Ollama with serve command
            cmd = [str(ollama_path), "serve"]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            process = psutil.Popen(cmd)
            self.processes["ollama"] = process
            
            # Wait for Ollama to start
            for attempt in range(30):  # 30 second timeout
                if await self.check_ollama_health(timeout=1.0):
                    logger.info("Ollama started successfully")
                    return True
                    
                # Check if process is still running
                if not process.is_running():
                    logger.error("Ollama process terminated unexpectedly")
                    return False
                    
                await asyncio.sleep(1)
                logger.info(f"Waiting for Ollama to start (attempt {attempt + 1}/30)...")
                
            logger.error("Ollama failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False
            
    async def start_api(self) -> bool:
        """Start API server."""
        if await self.check_api_health(timeout=1.0):
            logger.info("API is already running")
            return True
            
        if self.is_port_in_use(8000):
            logger.warning("Port 8000 is in use, attempting to kill existing process")
            if not self.kill_process_on_port(8000):
                logger.error("Failed to kill process on port 8000")
                return False
            # Wait for port to be released
            for _ in range(5):
                if not self.is_port_in_use(8000):
                    break
                await asyncio.sleep(1)
            else:
                logger.error("Port 8000 is still in use after killing process")
                return False
                
        try:
            # On Windows, we need to use python.exe explicitly
            python_exe = sys.executable
            if not python_exe:
                logger.error("Could not find Python executable")
                return False
                
            # Get the absolute path to the project root
            project_root = Path(__file__).parent.parent.parent.resolve()
            
            # Add project root to PYTHONPATH
            env = os.environ.copy()
            python_path = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{project_root};{python_path}" if python_path else str(project_root)
            
            # Start API server
            cmd = [
                python_exe,
                "-m", "uvicorn",
                "src.api.server:app",
                "--host=localhost",
                "--port=8000",
                "--log-level=info"  # Change to info for better debugging
            ]
            
            logger.info(f"Starting API server with command: {' '.join(cmd)}")
            logger.info(f"Working directory: {project_root}")
            
            # On Windows, we need to create a new process group to prevent the child from being killed
            # when the parent is terminated
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            
            process = psutil.Popen(
                cmd,
                cwd=str(project_root),  # Set working directory
                env=env,  # Pass environment variables
                stdout=None,  # Don't capture output for better logging
                stderr=None,
                creationflags=creation_flags  # Set creation flags for Windows
            )
            self.processes["api"] = process
            
            # Wait for API to start
            for attempt in range(30):  # 30 second timeout
                if await self.check_api_health(timeout=1.0):
                    logger.info("API started successfully")
                    return True
                    
                # Check if process is still running
                if not process.is_running():
                    logger.error("API process terminated unexpectedly")
                    return False
                    
                await asyncio.sleep(1)
                logger.info(f"Waiting for API to start (attempt {attempt + 1}/30)...")
                
            logger.error("API failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start API: {e}")
            return False
            
    def kill_streamlit_processes(self) -> bool:
        """Kill all Streamlit processes."""
        try:
            killed = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    # Check if this is a Streamlit process
                    if proc.name().lower() == 'streamlit' or proc.name().lower() == 'streamlit.exe':
                        proc.kill()
                        killed = True
                    elif proc.cmdline() and 'streamlit' in ' '.join(proc.cmdline()).lower():
                        proc.kill()
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            # Wait for processes to terminate
            if killed:
                psutil.wait_procs(
                    [p for p in psutil.process_iter() if 'streamlit' in p.name().lower()],
                    timeout=3
                )
            return True
        except Exception as e:
            logger.error(f"Failed to kill Streamlit processes: {e}")
            return False
            
    async def start_ui(self) -> bool:
        """Start UI service."""
        # First kill any existing Streamlit processes
        self.kill_streamlit_processes()
        
        # Wait for port to be released
        for _ in range(5):
            if not self.is_port_in_use(8501):
                break
            await asyncio.sleep(1)
        else:
            logger.error("Port 8501 is still in use after killing processes")
            return False
            
        try:
            # Get the absolute path to the project root
            project_root = Path(__file__).parent.parent.parent.resolve()
            
            # Add project root to PYTHONPATH
            env = os.environ.copy()
            python_path = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{project_root};{python_path}" if python_path else str(project_root)
            
            # Create a unique config directory for this instance
            config_dir = project_root / "temp" / f"streamlit_{os.getpid()}"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Set Streamlit config environment variables
            env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
            env['STREAMLIT_SERVER_PORT'] = '8501'
            env['STREAMLIT_SERVER_ADDRESS'] = 'localhost'
            env['STREAMLIT_SERVER_HEADLESS'] = 'true'
            env['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
            env['STREAMLIT_CONFIG_DIR'] = str(config_dir)
            
            # Set API port for UI
            env['API_PORT'] = str(self.config_manager.config.ports.api)
            
            cmd = [
                sys.executable,
                "-m", "streamlit",
                "run", "src/ui/app.py",
                "--server.port=8501",
                "--server.address=localhost",
                "--server.headless=true",
                "--server.fileWatcherType=none",
                "--browser.gatherUsageStats=false"
            ]
            
            # On Windows, we need to create a new process group
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            
            process = psutil.Popen(
                cmd,
                cwd=str(project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
                text=True
            )
            self.processes["ui"] = process
            
            # Wait for UI to start
            for attempt in range(30):
                if not self.is_port_in_use(8501):
                    await asyncio.sleep(1)
                    continue
                    
                # Check if process is still running
                if not process.is_running():
                    stdout, stderr = process.communicate()
                    logger.error(f"UI process terminated unexpectedly\nStdout: {stdout}\nStderr: {stderr}")
                    return False
                    
                # Try to connect to verify it's responding
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get('http://localhost:8501/_stcore/health', timeout=1) as response:
                            if response.status == 200:
                                logger.info("UI started successfully")
                                return True
                except Exception as e:
                    logger.debug(f"UI not ready yet: {e}")
                    await asyncio.sleep(1)
                    continue
                
            logger.error("UI failed to start within timeout")
            stdout, stderr = process.communicate()
            logger.error(f"UI process output:\nStdout: {stdout}\nStderr: {stderr}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start UI: {e}")
            return False
            
    async def stop_service(self, name: str):
        """Stop a service by name."""
        if name in self.processes:
            try:
                process = self.processes[name]
                if process.is_running():
                    # Special handling for UI service
                    if name == "ui":
                        # Kill the entire process tree
                        for child in process.children(recursive=True):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        process.kill()
                    else:
                        # Try graceful termination first
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            # Force kill if termination fails
                            process.kill()
                            process.wait(timeout=1)
                del self.processes[name]
                logger.info(f"Stopped {name} service")
            except Exception as e:
                logger.error(f"Error stopping {name} service: {e}")
                # Force kill as last resort
                try:
                    if name in self.processes:
                        self.processes[name].kill()
                except Exception:
                    pass
                
    async def stop_all_services(self):
        """Stop all services."""
        try:
            # Stop UI first to prevent orphaned processes
            if "ui" in self.processes:
                await self.stop_service("ui")
                
            # Then stop other services
            for name in list(self.processes.keys()):
                if name != "ui":
                    await self.stop_service(name)
                    
            # Clean up any remaining processes on our ports
            for port in [11434, 8000, 8501]:
                self.kill_process_on_port(port, force=True)
                
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
        finally:
            self.processes.clear()
            
    async def ensure_ports_available(self) -> bool:
        """Enhanced port conflict handling with OS-specific logging"""
        required_ports = {
            11434: "Ollama",
            8000: "API",
            8501: "UI"
        }
        
        for port, service in required_ports.items():
            if self.is_port_in_use(port):
                logger.warning(f"Port {port} ({service}) in use, attempting to free...")
                success = False
                
                # Get process info before killing
                try:
                    proc = self.get_process_on_port(port)
                    proc_info = f"{proc.name()} (PID: {proc.pid})" if proc else "unknown process"
                    logger.info(f"Conflicting process: {proc_info}")
                except Exception as e:
                    logger.debug(f"Process check error: {str(e)}")

                # Attempt to kill
                if self.kill_process_on_port(port, force=True):
                    # Wait for port release with backoff
                    wait_time = 1.0
                    for _ in range(5):
                        await asyncio.sleep(wait_time)
                        if not self.is_port_in_use(port):
                            success = True
                            break
                        wait_time *= 1.5
                    
                    if not success:
                        logger.error(f"Failed to free port {port} after 5 attempts")
                        return False
                else:
                    logger.error(f"Could not terminate process on port {port}")
                    return False
                    
        return True
            
    async def start_all_services(self) -> bool:
        """Start all services."""
        try:
            # First ensure all ports are available
            if not await self.ensure_ports_available():
                logger.error("Failed to ensure required ports are available")
                return False
                
            # Start Ollama first
            if not await self.start_ollama():
                logger.error("Failed to start Ollama")
                return False
                
            # Start API server
            if not await self.start_api():
                logger.error("Failed to start API")
                await self.stop_all_services()
                return False
                
            # Start UI last
            if not await self.start_ui():
                logger.error("Failed to start UI")
                await self.stop_all_services()
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            await self.stop_all_services()
            return False
            
    def get_process_on_port(self, port: int) -> Optional[psutil.Process]:
        """Get process using a specific port."""
        try:
            if sys.platform == 'win32':
                # On Windows, use netstat to find the process
                cmd = f'netstat -ano | findstr :{port}'
                output = subprocess.check_output(cmd, shell=True).decode()
                if output:
                    # Extract PID from the last line that has our port
                    for line in output.splitlines():
                        if f":{port}" in line:
                            try:
                                pid = int(line.strip().split()[-1])
                                return psutil.Process(pid)
                            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                                continue
            else:
                # On Unix-like systems, use lsof
                cmd = f'lsof -ti:{port}'
                try:
                    output = subprocess.check_output(cmd, shell=True).decode()
                    if output:
                        pid = int(output.strip())
                        return psutil.Process(pid)
                except (subprocess.CalledProcessError, ValueError, psutil.NoSuchProcess):
                    pass
        except Exception as e:
            logger.warning(f"Failed to get process on port {port}: {e}")
        return None

class OllamaClient:
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.gpu_layers = int(os.getenv('OLLAMA_GPU_LAYERS', '28'))
        self.num_gpu = int(os.getenv('CUDA_VISIBLE_DEVICES', '1'))
        
    async def generate(self, prompt: str, model: str, **kwargs):
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "options": {
                    "num_gpu": self.num_gpu,
                    "num_thread": int(os.getenv('OLLAMA_THREAD_COUNT', '8')),
                    "num_ctx": 4096
                },
                "stream": False
            }
            # ... rest of the method ... 