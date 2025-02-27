"""Streamlit UI for Local LLM Chat Interface."""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import os
import time

logger = logging.getLogger(__name__)

class UIServer:
    """Streamlit UI server for Local LLM Chat Interface."""
    
    def __init__(self, api_host: str = "localhost", api_port: int = 8000):
        """Initialize UI server.
        
        Args:
            api_host: API server hostname
            api_port: API server port
        """
        self.api_base_url = f"http://{api_host}:{api_port}"
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        async with self._lock:
            if not self._session or self._session.closed:
                self._session = aiohttp.ClientSession(
                    base_url=self.api_base_url,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
            return self._session
            
    async def close(self):
        """Close the UI server."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def health_check(self) -> bool:
        """Check if UI server is healthy."""
        try:
            # First check if the process is running
            if hasattr(self, '_process') and not self._process.is_running():
                logger.error("UI server process is not running")
                return False
                
            # Try to connect to the Streamlit server
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)  # 1 second timeout
                try:
                    s.connect(('localhost', 8501))
                    return True
                except (socket.timeout, ConnectionRefusedError) as e:
                    logger.debug(f"UI server not ready yet: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Error checking UI server health: {e}")
                    return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            session = await self.get_session()
            async with session.get("/models") as response:
                if response.status != 200:
                    raise Exception(f"Failed to list models: {response.status}")
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
            
    async def chat(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Chat with a model."""
        try:
            session = await self.get_session()
            async with session.post(
                "/chat",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"Chat failed: {response.status}")
                return await response.json()
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise
            
    def run(self):
        """Run the Streamlit UI."""
        # Set page config
        st.set_page_config(
            page_title="Lowkey Llama",
            page_icon="🦙",
            layout="wide"
        )
        
        # Add custom CSS
        st.markdown("""
            <style>
                .stTextInput > div > div > input {
                    background-color: #f0f2f6;
                }
                .stTextArea > div > div > textarea {
                    background-color: #f0f2f6;
                }
                .stSelectbox > div > div > select {
                    background-color: #f0f2f6;
                }
                .stSlider > div > div > div > div {
                    background-color: #f0f2f6;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        if "models" not in st.session_state:
            st.session_state.models = []
            
        # Title
        st.title("Lowkey Llama 🦙")
        
        # Sidebar
        with st.sidebar:
            st.header("Settings")
            
            # Model selection
            if not st.session_state.models:
                async def load_models():
                    models = await self.list_models()
                    st.session_state.models = models
                    
                asyncio.run(load_models())
                
            model = st.selectbox(
                "Model",
                options=st.session_state.models,
                index=0 if st.session_state.models else None,
                help="Select the model to chat with"
            )
            
            # System prompt
            system = st.text_area(
                "System Prompt",
                value="You are a helpful AI assistant.",
                help="Set the system prompt for the model"
            )
            
            # Temperature
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Control randomness in the model's responses"
            )
            
            # Max tokens
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=1,
                max_value=4096,
                value=2048,
                step=1,
                help="Maximum number of tokens in the response"
            )
            
            # Clear chat button
            if st.button("Clear Chat"):
                st.session_state.messages = []
                st.experimental_rerun()
                
        # Chat interface
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt := st.chat_input("Type your message here..."):
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": prompt
            })
            
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Get model response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                async def get_response():
                    try:
                        response = await self.chat(
                            model=model,
                            prompt=prompt,
                            system=system,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        
                        content = response.get("response", "")
                        message_placeholder.markdown(content)
                        
                        # Add assistant message
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": content
                        })
                        
                    except Exception as e:
                        message_placeholder.error(f"Error: {e}")
                        
                # Run in event loop
                loop = asyncio.new_event_loop()
                add_script_run_ctx(loop)
                asyncio.set_event_loop(loop)
                loop.run_until_complete(get_response())
                loop.close()
                
    async def start(self):
        """Start the UI server."""
        try:
            import sys
            import subprocess
            import psutil
            from pathlib import Path
            
            logger.info(f"Starting UI server with API endpoint: {self.api_base_url}")
            
            # Get the absolute path to the project root
            project_root = Path(__file__).parent.parent.parent.resolve()
            logger.debug(f"Project root: {project_root}")
            
            # Add project root to PYTHONPATH
            env = os.environ.copy()
            python_path = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{project_root};{python_path}" if python_path else str(project_root)
            
            # Set API configuration for UI
            env['API_HOST'] = 'localhost'
            env['API_PORT'] = str(self.api_base_url.split(':')[-1])
            logger.info(f"Setting API configuration - Host: {env['API_HOST']}, Port: {env['API_PORT']}")
            
            # Set Streamlit config environment variables
            env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
            env['STREAMLIT_SERVER_PORT'] = '8501'
            env['STREAMLIT_SERVER_ADDRESS'] = 'localhost'
            env['STREAMLIT_SERVER_HEADLESS'] = 'true'
            env['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
            
            # Create a unique config directory for this instance
            config_dir = project_root / "temp" / f"streamlit_{os.getpid()}"
            config_dir.mkdir(parents=True, exist_ok=True)
            env['STREAMLIT_CONFIG_DIR'] = str(config_dir)
            logger.debug(f"Streamlit config directory: {config_dir}")
            
            # Verify UI app exists
            ui_app_path = project_root / "src" / "ui" / "app.py"
            if not ui_app_path.exists():
                raise FileNotFoundError(f"UI app not found at {ui_app_path}")
            logger.info(f"Found UI app at: {ui_app_path}")
            
            # Prepare command
            cmd = [
                sys.executable,
                "-m", "streamlit",
                "run", str(ui_app_path),
                "--server.port=8501",
                "--server.address=localhost",
                "--server.headless=true",
                "--server.fileWatcherType=none",
                "--browser.gatherUsageStats=false"
            ]
            logger.debug(f"Starting UI server with command: {' '.join(cmd)}")
            
            # On Windows, we need to create a new process group
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            
            # Start the process with output redirection
            self._process = psutil.Popen(
                cmd,
                cwd=str(project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
                text=True  # Use text mode for output
            )
            
            logger.info(f"Started UI server process (PID: {self._process.pid})")
            
            # Wait for server to start with improved error handling
            timeout = 30  # Reduced timeout to 30 seconds
            start_time = time.time()
            last_log_time = 0
            log_interval = 5
            
            while time.time() - start_time < timeout:
                # Check process status first
                if not self._process.is_running():
                    stdout, stderr = self._process.communicate()
                    error_msg = "UI server process terminated unexpectedly"
                    logger.error(error_msg)
                    logger.error(f"Exit code: {self._process.returncode}")
                    if stdout: logger.error(f"stdout:\n{stdout}")
                    if stderr: logger.error(f"stderr:\n{stderr}")
                    raise Exception(f"{error_msg}\nExit code: {self._process.returncode}\nStderr: {stderr}")
                
                # Try health check
                try:
                    if await self.health_check():
                        logger.info("UI server started successfully")
                        return
                except Exception:
                    # Check for process output
                    stdout = self._process.stdout.readline() if self._process.stdout else ""
                    stderr = self._process.stderr.readline() if self._process.stderr else ""
                    
                    if stdout:
                        logger.info(f"UI server stdout: {stdout.strip()}")
                    if stderr:
                        logger.warning(f"UI server stderr: {stderr.strip()}")
                    
                    # Log progress periodically
                    current_time = time.time()
                    if current_time - last_log_time >= log_interval:
                        elapsed = int(current_time - start_time)
                        logger.info(f"Waiting for UI server to become healthy... ({elapsed}s/{timeout}s)")
                        last_log_time = current_time
                
                await asyncio.sleep(1)
            
            # If we get here, we've timed out
            error_msg = f"UI server failed to start within {timeout} seconds"
            logger.error(error_msg)
            
            # Collect final output
            stdout, stderr = self._process.communicate()
            if stdout: logger.error(f"Final stdout:\n{stdout}")
            if stderr: logger.error(f"Final stderr:\n{stderr}")
            
            # Kill the process
            try:
                self._process.kill()
            except Exception as kill_error:
                logger.error(f"Error killing UI server process: {kill_error}")
            
            raise TimeoutError(f"{error_msg}\nFinal stderr: {stderr}")
            
        except Exception as e:
            logger.error(f"Failed to start UI server: {e}")
            # Clean up process if it exists
            if hasattr(self, '_process') and self._process:
                try:
                    self._process.terminate()
                    await asyncio.sleep(1)
                    if self._process.is_running():
                        self._process.kill()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up UI server process: {cleanup_error}")
            raise  # Re-raise the exception to be handled by the caller
            
    async def stop(self):
        """Stop the UI server."""
        try:
            if hasattr(self, '_process') and self._process and self._process.is_running():
                # Kill the entire process tree
                for child in self._process.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                self._process.kill()
                self._process = None
                
            await self.close()
            
        except Exception as e:
            logger.error(f"Error stopping UI server: {e}")
            raise 