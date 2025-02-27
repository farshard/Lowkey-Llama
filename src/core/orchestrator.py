"""System orchestrator for Local LLM initialization."""

import os
import sys
import time
import asyncio
import logging
import platform
import subprocess
import requests
import aiohttp
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
import json

from core.dependencies import DependencyManager
from core.launcher import SystemInit
from ollama_server import OllamaServer
from core.ollama import OllamaClient

# Configure rich logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()

class SystemOrchestrator:
    """Orchestrates the initialization and management of all system components."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the orchestrator.
        
        Args:
            project_root: Path to project root. If None, will be auto-detected.
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.dependency_manager = DependencyManager(self.project_root)
        self.system_init = None
        self.ollama_server = OllamaServer()
        self.ollama_client = None
        
    async def _init_system(self):
        """Initialize the system components."""
        if not self.system_init:
            self.system_init = SystemInit()
            if not await self.system_init.initialize():
                raise Exception("Failed to initialize system configuration")
        
    async def _check_port(self, port: int, retries: int = 5, delay: float = 1.0) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port number to check
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            bool: True if port is available, False if in use
        """
        import socket
        
        # First try to kill any existing process on the port
        process_info = self._get_process_on_port(port)
        
        # Retry getting process info a few times to mitigate race conditions
        for retry_get_process in range(3):
            if process_info:
                break # Found process info, proceed
            else:
                await asyncio.sleep(0.2) # Small delay before retry
                process_info = self._get_process_on_port(port) # Retry get process info
                
        if process_info: # Process info found (either initially or after retries)
            pid, name = process_info
            logger.warning(f"Port {port} is in use by {name} (PID: {pid})") # Log process name from tasklist
            if name.lower() in ['python.exe', 'pythonw.exe', 'python3.exe', 'python3.13.exe']: # Check process name
                logger.info(f"Attempting to kill process on port {port}") # Log before kill attempt
                if await self._kill_process_on_port(port): # Await kill process
                    # Wait for the process to fully terminate
                    for _ in range(3): # Wait up to 3 times
                        await asyncio.sleep(delay) # Wait delay
                        if not self._get_process_on_port(port): # Check if process is gone
                            break # Process gone, break wait loop
        
        # Now check if the port is available after (potentially) killing process
        for i in range(retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return True
            except OSError:
                if i < retries - 1:
                    await asyncio.sleep(delay)
                continue
        return False
        
    async def ensure_dependencies(self) -> bool:
        """Ensure all dependencies are installed and up to date."""
        with console.status("[bold blue]Checking dependencies...") as status:
            try:
                if not self.dependency_manager.ensure_dependencies():
                    logger.error("Failed to install dependencies")
                    return False
                    
                logger.info("Dependencies verified")
                return True
                
            except Exception as e:
                logger.error(f"Dependency check failed: {e}")
                return False
                
    async def ensure_ollama(self) -> bool:
        """Ensure Ollama is installed, running, and has required models."""
        with console.status("[bold blue]Checking Ollama...") as status:
            try:
                # Create Ollama client and use as context manager
                async with OllamaClient() as client:
                    # Check if Ollama is already running
                    if await client.health_check():
                        logger.info("Using existing Ollama server")
                    else:
                        # Start Ollama server if not running
                        if not self.ollama_server.start():
                            logger.error("Failed to start Ollama server")
                            return False
                        
                        # Wait for server to be ready
                        for _ in range(5):
                            if await client.health_check():
                                break
                            await asyncio.sleep(2)
                        else:
                            logger.error("Ollama server failed to respond")
                            return False
                        
                    # Check for default model
                    models = await client.list_models()
                    if not hasattr(self.system_init, 'config'):
                        logger.error("System configuration not loaded")
                        return False
                        
                    default_model = getattr(self.system_init.config, 'default_model', 'mistral')
                    logger.info(f"Checking default model: {default_model}")
                    
                    # Handle model requirements
                    if not models:
                        logger.error("No models found")
                        return False
                        
                    # For custom models like mistral-fixed, check if base model exists
                    is_custom_model = "-" in default_model
                    base_model = default_model.split("-")[0] if is_custom_model else default_model
                    
                    # Check if the default model exists in the available models
                    model_exists = default_model in models
                    
                    # If the model doesn't exist, we need to either pull it or create it
                    if not model_exists:
                        # Check if it's a custom model that needs to be created from a modelfile
                        if is_custom_model:
                            logger.info(f"Default model {default_model} not found - checking if it's a custom model")
                            
                            # First ensure the base model exists
                            if base_model not in models:
                                logger.info(f"Pulling base model for custom model: {base_model}")
                                try:
                                    async for progress in client.pull_model(base_model):
                                        if "status" in progress and "completed" in progress and "total" in progress:
                                            status_msg = f"Pulling {base_model}: {progress['completed']}/{progress['total']} MB"
                                            status.update(f"[bold blue]{status_msg}")
                                except Exception as e:
                                    logger.error(f"Failed to pull base model: {e}")
                                    return False
                            
                            # Now try to create the custom model
                            modelfile_path = Path(self.project_root) / "models" / f"{default_model}.modelfile"
                            if modelfile_path.exists():
                                logger.info(f"Creating custom model {default_model} from modelfile")
                                ollama_path = getattr(self.system_init.config.paths, 'ollama', 'ollama')
                                
                                # Use subprocess to run the create command
                                try:
                                    cmd = [ollama_path, "create", default_model, "-f", str(modelfile_path)]
                                    logger.debug(f"Running command: {' '.join(cmd)}")
                                    
                                    # Use subprocess with async
                                    proc = await asyncio.create_subprocess_exec(
                                        *cmd,
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE
                                    )
                                    stdout, stderr = await proc.communicate()
                                    
                                    if proc.returncode != 0:
                                        logger.error(f"Failed to create custom model: {stderr.decode()}")
                                        # Fall back to using base model
                                        logger.info(f"Falling back to base model: {base_model}")
                                        self.system_init.config.default_model = base_model
                                        await self._save_config()
                                    else:
                                        logger.info(f"Successfully created custom model {default_model}")
                                        model_exists = True  # Set this to True since we just created the model
                                except Exception as e:
                                    logger.error(f"Failed to create custom model: {e}")
                                    # Fall back to using base model
                                    logger.info(f"Falling back to base model: {base_model}")
                                    self.system_init.config.default_model = base_model
                                    await self._save_config()
                            else:
                                logger.error(f"Modelfile for {default_model} not found at {modelfile_path}")
                                # Fall back to using base model
                                logger.info(f"Falling back to base model: {base_model}")
                                self.system_init.config.default_model = base_model
                                await self._save_config()
                        else:
                            # For non-custom models, try to pull the model directly
                            logger.info(f"Pulling model: {default_model}")
                            try:
                                async for progress in client.pull_model(default_model):
                                    if "status" in progress and "completed" in progress and "total" in progress:
                                        status_msg = f"Pulling {default_model}: {progress['completed']}/{progress['total']} MB"
                                        status.update(f"[bold blue]{status_msg}")
                            except Exception as e:
                                logger.error(f"Failed to pull model: {e}")
                                return False
                    
                    # Test model with simple inference - use the model that should be available at this point
                    test_model = default_model if default_model in await client.list_models() else base_model
                    logger.info(f"Testing model: {test_model}")
                    
                    try:
                        # Use our fixed chat method instead of generate
                        response = await client.chat(
                            model=test_model,
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": "Hello, tell me about dogs in one sentence."}
                            ],
                            options={
                                "temperature": 0.7,
                                "num_predict": 100
                            }
                        )
                        
                        if not response or "message" not in response:
                            logger.error(f"Model test failed: Invalid response format")
                            return False
                            
                        logger.info(f"Model test successful")
                        return True
                    except Exception as e:
                        logger.error(f"Model test failed: {e}")
                        return False
                    
            except Exception as e:
                logger.error(f"Ollama check failed: {e}")
                return False
                
    async def _save_config(self) -> bool:
        """Save the current configuration to file."""
        try:
            config_path = Path(self.project_root) / "config.json"
            config_dict = self.system_init.config.model_dump()
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=4)
            logger.info("Configuration updated and saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    async def ensure_api_server(self) -> bool:
        """Ensure API server is running and healthy."""
        with console.status("[bold blue]Starting API server...") as status:
            try:
                # Get default port and fallback ports
                default_port = self.system_init.config.ports.api
                fallback_ports = [8001, 8002, 8003, 8004, 8005]  # List of fallback ports to try
                
                # Try default port first
                port_to_use = default_port
                port_available = await self._check_port(port_to_use)
                
                # If default port is not available, try fallback ports
                if not port_available:
                    logger.warning(f"Default port {default_port} is unavailable, trying fallback ports...")
                    for port in fallback_ports:
                        if await self._check_port(port):
                            port_to_use = port
                            port_available = True
                            logger.info(f"Using fallback port {port}")
                            break
                            
                if not port_available:
                    logger.error("No available ports found")
                    return False
                    
                # Update config with the port we're using
                self.system_init.config.ports.api = port_to_use
                
                # Save the updated configuration
                await self._save_config()
                
                # Initialize API server if not already initialized
                if not hasattr(self.system_init, 'api_server') or not self.system_init.api_server:
                    api_host = self.system_init.config.hosts.api
                    from core.api import APIServer
                    self.system_init.api_server = APIServer(host=api_host, port=port_to_use)
                
                # Start API server with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Start the server
                        await self.system_init.api_server.start()
                        
                        # Wait for server to be healthy with timeout
                        timeout = 30  # 30 seconds timeout
                        start_time = time.time()
                        
                        while time.time() - start_time < timeout:
                            try:
                                if await self.system_init.api_server.health_check():
                                    logger.info(f"API server started and healthy on port {port_to_use}")
                                    return True
                            except Exception as e:
                                logger.debug(f"Health check attempt failed: {e}")
                            await asyncio.sleep(1)
                            status.update(f"[bold blue]Waiting for API server to be ready... ({int(time.time() - start_time)}s)")
                            
                        # If we get here, server didn't become healthy in time
                        if attempt < max_retries - 1:
                            logger.warning(f"API server health check timed out, retrying... (attempt {attempt + 1}/{max_retries})")
                            await self.system_init.api_server.stop()
                            await asyncio.sleep(2)
                        else:
                            logger.error("API server failed to become healthy after retries")
                            return False
                            
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to start API server, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"API server start failed: {e}")
                            return False
                            
                return False
                
            except Exception as e:
                logger.error(f"API server initialization failed: {e}")
                return False
                
    async def ensure_ui_server(self) -> bool:
        """Ensure UI server is running and healthy."""
        with console.status("[bold blue]Starting UI server...") as status:
            try:
                logger.info("Initializing UI server...")
                
                # Get default port and fallback ports
                default_port = self.system_init.config.ports.ui
                fallback_ports = [8502, 8503, 8504, 8505]  # List of fallback ports to try
                
                # Try default port first
                port_to_use = default_port
                port_available = await self._check_port(port_to_use)
                
                # If default port is not available, try fallback ports
                if not port_available:
                    logger.warning(f"Default port {default_port} is unavailable, trying fallback ports...")
                    for port in fallback_ports:
                        if await self._check_port(port):
                            port_to_use = port
                            port_available = True
                            logger.info(f"Using fallback port {port}")
                            break
                            
                if not port_available:
                    logger.error("No available ports found for UI server")
                    return False
                    
                # Update config with the port we're using
                self.system_init.config.ports.ui = port_to_use
                
                # Save the updated configuration
                await self._save_config()
                
                # Initialize UI server if not already initialized
                if not hasattr(self.system_init, 'ui_server') or not self.system_init.ui_server:
                    logger.info("Creating UI server instance...")
                    api_host = self.system_init.config.hosts.api
                    api_port = self.system_init.config.ports.api
                    from core.ui import UIServer
                    self.system_init.ui_server = UIServer(api_host=api_host, api_port=api_port)
                
                # Start UI server with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Starting UI server (attempt {attempt + 1}/{max_retries})...")
                        # Start the server
                        await self.system_init.ui_server.start()
                        
                        # Wait for server to be healthy with timeout
                        timeout = 30  # 30 seconds timeout
                        start_time = time.time()
                        
                        while time.time() - start_time < timeout:
                            try:
                                if await self.system_init.ui_server.health_check():
                                    logger.info(f"UI server started and healthy on port {port_to_use}")
                                    return True
                            except Exception as e:
                                logger.debug(f"UI health check attempt failed: {e}")
                            await asyncio.sleep(1)
                            status.update(f"[bold blue]Waiting for UI server to be ready... ({int(time.time() - start_time)}s)")
                            
                        # If we get here, server didn't become healthy in time
                        if attempt < max_retries - 1:
                            logger.warning(f"UI server health check timed out, retrying... (attempt {attempt + 1}/{max_retries})")
                            await self.system_init.ui_server.stop()
                            await asyncio.sleep(2)
                        else:
                            logger.error("UI server failed to become healthy after retries")
                            return False
                            
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to start UI server, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"UI server start failed: {e}")
                            return False
                            
                return False
                
            except Exception as e:
                logger.error(f"UI server initialization failed: {e}")
                logger.error(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
                return False
                
    async def initialize(self) -> bool:
        """Initialize and run the system."""
        try:
            console.rule("[bold blue]Lowkey Llama - System Initialization")
            
            # Initialize system first
            await self._init_system()
            
            # Initialize system components
            steps = [
                ("Dependencies", self.ensure_dependencies),
                ("Ollama", self.ensure_ollama),
                ("API Server", self.ensure_api_server),
                ("UI Server", self.ensure_ui_server)
            ]
            
            for name, step in steps:
                try:
                    if not await step():
                        logger.error(f"{name} initialization failed")
                        await self.cleanup()
                        return False
                except Exception as e:
                    logger.error(f"{name} initialization failed: {e}")
                    await self.cleanup()
                    return False
            
            console.rule("[bold green]Initialization Complete")
            logger.info("System is ready!")
            
            # Keep the application running until interrupted
            try:
                # Create an event to keep the main task running
                running = asyncio.Event()
                await running.wait()
            except asyncio.CancelledError:
                logger.info("Received shutdown signal")
            finally:
                await self.cleanup()
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            await self.cleanup()
            return False
            
    async def cleanup(self):
        """Clean up all system resources."""
        try:
            # Stop servers in reverse order
            if hasattr(self.system_init, 'ui_server') and self.system_init.ui_server:
                try:
                    await self.system_init.ui_server.stop()
                except Exception as e:
                    logger.error(f"Failed to stop UI server: {e}")
                    
            if hasattr(self.system_init, 'api_server') and self.system_init.api_server:
                try:
                    # Properly terminate the API server process
                    if hasattr(self.system_init.api_server, 'process'):
                        process = self.system_init.api_server.process
                        if process and process.returncode is None:
                            process.terminate()
                            try:
                                await asyncio.wait_for(process.wait(), timeout=5.0)
                            except asyncio.TimeoutError:
                                process.kill()  # Force kill if graceful termination fails
                    await self.system_init.api_server.stop()
                except Exception as e:
                    logger.error(f"Failed to stop API server: {e}")
                    
            # Kill any remaining processes on our ports
            ports = [
                self.system_init.config.ports.api,
                self.system_init.config.ports.ui
            ]
            for port in ports:
                try:
                    if await self._check_port(port):
                        await self._kill_process_on_port(port)
                except Exception as e:
                    logger.error(f"Failed to kill process on port {port}: {e}")
                    
            # Clean up any temporary files
            try:
                temp_dir = Path(self.project_root) / "temp"
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
            logger.error(f"Cleanup failed: {e}")
            # Don't re-raise - we want to attempt all cleanup steps
            
    def _get_process_on_port(self, port: int) -> Optional[Tuple[int, str]]:
        """Get process ID and name using port on Windows."""
        try:
            # Use more specific netstat filter to only get listening or established connections
            cmd = f'netstat -ano | findstr ":{port}" | findstr /i "listening established"'
            logger.debug(f"Running netstat command: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            logger.debug(f"Raw netstat output: {result.stdout}")
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the line to get PID - split and get last item
                lines = result.stdout.strip().split('\n')
                logger.debug(f"Found {len(lines)} potential connections on port {port}")
                
                for line in lines:
                    logger.debug(f"Processing netstat line: {line}")
                    parts = line.strip().split()
                    if len(parts) >= 5:  # Ensure we have enough parts
                        try:
                            pid = int(parts[-1])  # Last part should be PID
                            logger.debug(f"Found PID {pid} on port {port}")
                            
                            # Get process name with error handling
                            cmd = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
                            logger.debug(f"Running tasklist command: {cmd}")
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            logger.debug(f"Tasklist output: {result.stdout}")
                            
                            if result.returncode == 0:
                                output = result.stdout.strip()
                                if output.startswith("INFO: No tasks"):
                                    # This is a zombie process - return special marker
                                    logger.warning(f"Found zombie process with PID {pid} on port {port}")
                                    return pid, "ZOMBIE"
                                elif output and not output.startswith("INFO:"):
                                    # Parse CSV format properly
                                    import csv
                                    from io import StringIO
                                    reader = csv.reader(StringIO(output))
                                    row = next(reader, None)
                                    if row and len(row) > 0:
                                        logger.debug(f"Found process name: {row[0]} for PID {pid}")
                                        return pid, row[0]  # First column is process name
                                    else:
                                        logger.debug(f"No valid CSV data found for PID {pid}")
                                else:
                                    logger.debug(f"Skipping info message from tasklist: {output}")
                            else:
                                logger.debug(f"Tasklist command failed for PID {pid}")
                        except (ValueError, StopIteration) as e:
                            logger.debug(f"Error processing PID for line '{line}': {e}")
                            continue
                    else:
                        logger.debug(f"Netstat line has insufficient parts: {line}")
                    
            else:
                logger.debug(f"No connections found on port {port}")
            return None
        except Exception as e:
            logger.error(f"Error getting process on port {port}: {e}")
            return None
            
    async def _kill_process_on_port(self, port: int) -> bool:
        """Kill process using port on Windows."""
        try:
            logger.debug(f"Attempting to identify process on port {port}")
            process_info = self._get_process_on_port(port)
            
            if process_info:
                pid, name = process_info
                logger.debug(f"Found process to kill: {name} (PID: {pid}) on port {port}")
                
                # Special handling for zombie processes
                if name == "ZOMBIE":
                    logger.warning(f"Attempting to kill zombie process (PID: {pid}) on port {port}")
                    # Try a series of increasingly aggressive methods
                    methods = [
                        # PowerShell commands first
                        ('powershell -Command "Stop-Process -Id {pid} -Force"', False),
                        ('powershell -Command "Get-NetTCPConnection -LocalPort {port} | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force }}"', False),
                        # Then CMD commands
                        ("taskkill /F /PID {pid}", False),
                        ("taskkill /F /T /PID {pid}", True),
                        # Then network commands
                        ("netsh int ipv4 delete excludedportrange protocol=tcp startport={port} numberofports=1", True),
                        ("netsh int ipv4 add excludedportrange protocol=tcp startport={port} numberofports=1", True),
                        # Last resort - try to reset TCP stack
                        ('powershell -Command "Set-NetTCPSetting -SettingName InternetCustom -AutoTuningLevelLocal Disabled"', True),
                        ('powershell -Command "Set-NetTCPSetting -SettingName InternetCustom -AutoTuningLevelLocal Normal"', True),
                        ("netsh winsock reset", True),
                        ("netsh int ip reset", True)
                    ]
                    
                    for cmd_template, needs_admin in methods:
                        try:
                            cmd = cmd_template.format(pid=pid, port=port)
                            if needs_admin:
                                # Use runas to elevate privileges
                                cmd = f'powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/c,{cmd}\'"'
                            logger.debug(f"Executing command: {cmd}")
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            logger.debug(f"Command output: stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}', returncode={result.returncode}")
                            await asyncio.sleep(2)
                            
                            # Check if port is now free
                            if not self._get_process_on_port(port):
                                logger.info(f"Successfully killed zombie process on port {port}")
                                return True
                        except Exception as e:
                            logger.debug(f"Command failed: {e}")
                            continue
                    
                    # If all methods failed, suggest manual intervention
                    logger.error(f"Failed to kill zombie process on port {port}. Please try restarting your computer.")
                    return False
                
                # Normal process killing logic
                for attempt in range(3):
                    logger.info(f"Attempt {attempt + 1}: Killing process {name} (PID: {pid}) on port {port}")
                    
                    # First try graceful termination with PowerShell
                    kill_command = f'powershell -Command "Stop-Process -Id {pid}"'
                    logger.debug(f"Executing graceful kill: {kill_command}")
                    result = subprocess.run(kill_command, shell=True, capture_output=True, text=True)
                    logger.debug(f"Graceful kill output: stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}', returncode={result.returncode}")
                    await asyncio.sleep(2)
                    
                    # Verify if process is gone
                    check_result = self._get_process_on_port(port)
                    if not check_result:
                        logger.info(f"Process {name} (PID: {pid}) on port {port} gracefully terminated.")
                        return True
                    else:
                        logger.debug(f"Process still exists after graceful kill: {check_result}")
                    
                    # If still running, force kill with PowerShell
                    force_kill_command = f'powershell -Command "Stop-Process -Id {pid} -Force"'
                    logger.debug(f"Executing force kill: {force_kill_command}")
                    force_result = subprocess.run(force_kill_command, shell=True, capture_output=True, text=True)
                    logger.debug(f"Force kill output: stdout='{force_result.stdout.strip()}', stderr='{force_result.stderr.strip()}', returncode={force_result.returncode}")
                    await asyncio.sleep(2)
                    
                    # Verify again
                    check_result = self._get_process_on_port(port)
                    if not check_result:
                        logger.info(f"Process {name} (PID: {pid}) on port {port} force-killed.")
                        return True
                    else:
                        logger.debug(f"Process still exists after force kill: {check_result}")
                    
                    logger.warning(f"Process {name} (PID: {pid}) still running on port {port} after attempt {attempt + 1}.")
                    await asyncio.sleep(1)
                
                logger.error(f"Failed to kill process {name} (PID: {pid}) on port {port} after multiple attempts.")
                return False
                
            else:
                logger.debug(f"No process found on port {port}")
                return True  # No process to kill
        except Exception as e:
            logger.error(f"Error killing process on port {port}: {e}")
            return False

    async def _wait_for_api_ready(self, timeout=30):
        """Wait for API server to become ready"""
        start_time = time.time()
        time.sleep(2)  # Add a small initial delay
        logger.info("Waiting for API server to become ready...")
        while time.time() - start_time < timeout:
            try:
                logger.debug("Sending health check request to API server...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{self.system_init.config.ports.api}",
                        timeout=2
                    ) as response:
                        logger.debug(f"Health check response: {response.status}")
                        if response.status == 200:
                            return True
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(0.5)
                continue
        return False

def main():
    """Main entry point for system initialization."""
    try:
        # Create and get event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create orchestrator
        orchestrator = SystemOrchestrator()
        
        try:
            # Run initialization
            loop.run_until_complete(orchestrator.initialize())
            
            # Keep the loop running to maintain the servers
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Run cleanup
            loop.run_until_complete(orchestrator.cleanup())
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for task cancellation with timeout
            if pending:
                loop.run_until_complete(
                    asyncio.wait(pending, timeout=5.0)
                )
            
            # Close the loop properly
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True))
            except Exception as e:
                logger.debug(f"Error during final cleanup: {e}")
            finally:
                loop.stop()
                loop.close()
                
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 