import subprocess
import time
import sys
import os
import signal
import requests
import psutil
import webbrowser
import platform
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, List
import logging
import socket
from importlib.util import find_spec

class ServiceLauncher:
    def __init__(self):
        self.processes = {}
        self.base_dir = Path(__file__).parent.parent.resolve()
        self.platform = platform.system().lower()
        self.python_cmd = sys.executable
        self.setup_logging()
        self.config = self.load_config()
        self.temp_dir = self.setup_temp_dir()
        
        # Set up signal handlers for graceful shutdown
        if self.platform != 'windows':
            signal.signal(signal.SIGTERM, self.handle_shutdown)
            signal.signal(signal.SIGINT, self.handle_shutdown)
        else:
            signal.signal(signal.SIGINT, self.handle_shutdown)
            signal.signal(signal.SIGTERM, self.handle_shutdown)

    def setup_logging(self):
        """Set up logging configuration"""
        log_dir = self.base_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'app.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ServiceLauncher')

    def setup_temp_dir(self) -> Path:
        """Set up temporary directory for the application"""
        if self.platform == 'windows':
            base_temp = Path(os.getenv('TEMP', os.path.expanduser('~\\AppData\\Local\\Temp')))
        else:
            base_temp = Path('/tmp')
        temp_dir = base_temp / 'local-llm'
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def load_config(self) -> Dict:
        """Load configuration from config.json or use defaults"""
        config_file = self.base_dir / 'config.json'
        default_config = {
            'ports': {
                'ollama': 11434,
                'api': 8000,
                'streamlit': 8501
            },
            'hosts': {
                'ollama': 'localhost',
                'api': 'localhost',
                'streamlit': 'localhost'
            },
            'auto_open_browser': True,
            'default_model': 'mistral',
            'log_level': 'info',
            'hardware': self.detect_hardware()
        }
        
        if config_file.exists():
            try:
                with open(config_file) as f:
                    user_config = json.load(f)
                    # Deep merge configs
                    return self.deep_merge(default_config, user_config)
            except json.JSONDecodeError:
                self.logger.warning("Invalid config.json, using defaults")
                return default_config
        return default_config

    def detect_hardware(self) -> Dict:
        """Detect hardware capabilities"""
        hw_info = {
            'cpu_count': 1,  # Fallback values
            'cpu_threads': 1,
            'ram_gb': 4,
            'gpu': None,
            'platform': {
                'system': platform.system(),
                'machine': platform.machine(),
                'is_arm': platform.machine().lower() in ('arm64', 'aarch64'),
                'is_windows': platform.system().lower() == 'windows'
            }
        }
        
        # Safely get CPU info
        try:
            hw_info.update({
                'cpu_count': psutil.cpu_count(logical=False) or 1,
                'cpu_threads': psutil.cpu_count(logical=True) or 1,
                'ram_gb': round(psutil.virtual_memory().total / (1024**3), 1)
            })
        except Exception as e:
            self.logger.warning(f"Error detecting CPU/RAM info: {str(e)}")
        
        # Check for GPU capabilities
        if find_spec("torch") is not None:
            try:
                import torch
                if torch.cuda.is_available():
                    hw_info['gpu'] = {
                        'name': torch.cuda.get_device_name(0),
                        'vram_gb': round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1),
                        'cuda_version': torch.version.cuda,
                        'is_mps_available': hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
                    }
                elif hw_info['platform']['is_arm'] and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    hw_info['gpu'] = {
                        'name': 'Apple Silicon',
                        'type': 'mps',
                        'is_mps_available': True
                    }
            except Exception as e:
                self.logger.warning(f"Error detecting GPU info: {str(e)}")
        
        return hw_info

    def deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_ollama_cmd(self) -> List[str]:
        """Get platform-specific Ollama command"""
        if self.platform == 'windows':
            ollama_path = os.path.join(os.getenv('PROGRAMFILES', 'C:\\Program Files'), 'Ollama', 'ollama.exe')
            return [ollama_path, 'serve']
        elif self.platform == 'darwin':  # macOS
            if platform.machine() == 'arm64':
                return ['/opt/homebrew/bin/ollama', 'serve']
            return ['/usr/local/bin/ollama', 'serve']
        else:  # Linux
            return ['/usr/local/bin/ollama', 'serve']

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except:
            return False

    def check_ollama(self) -> bool:
        """Check if Ollama is running and start it if needed"""
        ollama_url = f"http://{self.config['hosts']['ollama']}:{self.config['ports']['ollama']}"
        
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.logger.info("✓ Ollama is running")
                # Pull default model if specified
                if self.config.get('default_model'):
                    if not self.pull_model(self.config['default_model']):
                        self.logger.warning("Failed to pull default model, but continuing...")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.Timeout:
            self.logger.error("Timeout while checking Ollama")
            return False

        self.logger.info("Starting Ollama...")
        try:
            # Check if port is available
            if not self.check_port_available(self.config['ports']['ollama']):
                self.logger.error(f"Port {self.config['ports']['ollama']} is already in use")
                return False

            process = subprocess.Popen(
                self.get_ollama_cmd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.platform == 'windows' else 0
            )
            self.processes['ollama'] = process
            
            # Wait for Ollama to start
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{ollama_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        self.logger.info("✓ Ollama started successfully")
                        # Pull default model if specified
                        if self.config.get('default_model'):
                            if not self.pull_model(self.config['default_model']):
                                self.logger.warning("Failed to pull default model, but continuing...")
                        return True
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    if i < max_retries - 1:
                        time.sleep(1)
                        continue
                    self.logger.error("✗ Failed to start Ollama")
                    return False
        except FileNotFoundError:
            self.logger.error("✗ Ollama not found. Please install it first.")
            if self.platform == 'darwin':
                print("Install with: brew install ollama")
            else:
                print("Visit: https://ollama.ai/download")
            return False
        except Exception as e:
            self.logger.error(f"Error starting Ollama: {str(e)}")
            return False

    def pull_model(self, model_name: str) -> bool:
        """Pull a model if it's not already downloaded"""
        self.logger.info(f"Checking model {model_name}...")
        ollama_cmd = self.get_ollama_cmd()[0].replace(' serve', '').split('/')[-1]  # Get just the command name
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # First check if model exists
                check_cmd = [ollama_cmd, 'list']
                result = subprocess.run(check_cmd, capture_output=True, text=True)
                if model_name in result.stdout:
                    self.logger.info(f"✓ Model {model_name} is already downloaded")
                    return True
                
                # If not, pull it
                self.logger.info(f"Pulling model {model_name} (attempt {attempt + 1}/{max_retries})...")
                pull_cmd = [ollama_cmd, 'pull', model_name]
                result = subprocess.run(
                    pull_cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"✓ Model {model_name} is ready")
                return True
                
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to pull model {model_name} (attempt {attempt + 1}): {e.stderr}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retrying
                else:
                    self.logger.error(f"✗ Failed to pull model {model_name} after {max_retries} attempts")
                    return False
            except Exception as e:
                self.logger.error(f"✗ Error pulling model {model_name}: {str(e)}")
                return False
        return False

    def cleanup(self):
        """Clean up temporary files and resources"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.logger.info("Cleaned up temporary files")
        except Exception as e:
            self.logger.error(f"Error cleaning up: {str(e)}")

    def start_api_server(self) -> bool:
        """Start the FastAPI server"""
        api_file = self.base_dir / 'src' / 'api_server.py'
        if not api_file.exists():
            print("✗ API server file not found")
            return False

        print("Starting API server...")
        env = os.environ.copy()
        env['API_PORT'] = str(self.config['ports']['api'])
        env['API_HOST'] = self.config['hosts']['api']
        
        api_cmd = [
            self.python_cmd, 
            str(api_file),
            '--host', self.config['hosts']['api'],
            '--port', str(self.config['ports']['api'])
        ]
        
        process = subprocess.Popen(
            api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.platform == 'windows' else 0
        )
        self.processes['api'] = process

        # Wait for API server to start
        api_url = f"http://{self.config['hosts']['api']}:{self.config['ports']['api']}"
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{api_url}/docs")
                if response.status_code == 200:
                    print("✓ API server started successfully")
                    return True
            except requests.exceptions.ConnectionError:
                if i < max_retries - 1:
                    time.sleep(1)
                    continue
                print("✗ Failed to start API server")
                return False

    def start_streamlit(self) -> bool:
        """Start the Streamlit interface"""
        streamlit_file = self.base_dir / 'src' / 'chat_app.py'
        if not streamlit_file.exists():
            print("✗ Streamlit app file not found")
            return False

        print("Starting Streamlit interface...")
        env = os.environ.copy()
        env['STREAMLIT_SERVER_PORT'] = str(self.config['ports']['streamlit'])
        env['STREAMLIT_SERVER_ADDRESS'] = self.config['hosts']['streamlit']
        
        streamlit_cmd = [
            self.python_cmd,
            '-m', 'streamlit',
            'run',
            str(streamlit_file),
            '--server.address', self.config['hosts']['streamlit'],
            '--server.port', str(self.config['ports']['streamlit'])
        ]
        
        process = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.platform == 'windows' else 0
        )
        self.processes['streamlit'] = process

        # Wait for Streamlit to start
        streamlit_url = f"http://{self.config['hosts']['streamlit']}:{self.config['ports']['streamlit']}"
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(streamlit_url)
                if response.status_code == 200:
                    print("✓ Streamlit interface started successfully")
                    return True
            except requests.exceptions.ConnectionError:
                if i < max_retries - 1:
                    time.sleep(1)
                    continue
                print("✗ Failed to start Streamlit interface")
                return False

    def handle_shutdown(self, signum: Optional[int] = None, frame: Optional[object] = None) -> None:
        """Handle graceful shutdown of all processes"""
        self.logger.info("\nShutting down services...")
        
        for name, process in self.processes.items():
            self.logger.info(f"Stopping {name}...")
            try:
                if self.platform == 'windows':
                    if name == 'ollama':
                        # On Windows, we need to kill Ollama differently
                        for proc in psutil.process_iter(['pid', 'name']):
                            if proc.info['name'] == 'ollama.exe':
                                proc.kill()
                    else:
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
                
                process.wait(timeout=5)
                self.logger.info(f"✓ {name} stopped")
            except (subprocess.TimeoutExpired, psutil.NoSuchProcess):
                self.logger.warning(f"! Forcing {name} to stop")
                try:
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
            except Exception as e:
                self.logger.error(f"! Error stopping {name}: {str(e)}")

        # Clean up
        self.cleanup()
        self.logger.info("All services stopped")
        sys.exit(0)

    def launch(self) -> None:
        """Launch all services"""
        self.logger.info(f"Starting Local LLM Chat Interface on {self.platform.capitalize()}...")
        
        # Check hardware compatibility
        hw = self.config['hardware']
        if hw['ram_gb'] < 8:
            self.logger.warning(f"Low RAM detected: {hw['ram_gb']:.1f}GB (8GB recommended)")
        if not hw.get('gpu'):
            self.logger.warning("No GPU detected, performance may be limited")
        
        if not self.check_ollama():
            return
        
        if not self.start_api_server():
            self.handle_shutdown()
            return
        
        if not self.start_streamlit():
            self.handle_shutdown()
            return

        # Open the web interface
        streamlit_url = f"http://{self.config['hosts']['streamlit']}:{self.config['ports']['streamlit']}"
        api_url = f"http://{self.config['hosts']['api']}:{self.config['ports']['api']}"
        
        if self.config['auto_open_browser']:
            webbrowser.open(streamlit_url)
        
        self.logger.info("\n" + "="*50)
        self.logger.info("All services started successfully!")
        self.logger.info(f"Web interface: {streamlit_url}")
        self.logger.info(f"API documentation: {api_url}/docs")
        self.logger.info("\nPress Ctrl+C to stop all services")
        self.logger.info("="*50 + "\n")

        # Keep the script running and monitor processes
        try:
            while True:
                time.sleep(1)
                # Check if any process has died
                for name, process in self.processes.items():
                    if process.poll() is not None:
                        self.logger.error(f"✗ {name} has stopped unexpectedly")
                        self.handle_shutdown()
                        return
        except KeyboardInterrupt:
            self.handle_shutdown()

if __name__ == "__main__":
    launcher = ServiceLauncher()
    launcher.launch() 