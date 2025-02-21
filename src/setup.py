import subprocess
import sys
import os
import platform
from pathlib import Path
import cpuinfo
import psutil
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

def check_hardware_compatibility():
    """Check if hardware meets minimum requirements"""
    cpu_info = cpuinfo.get_cpu_info()
    ram_gb = psutil.virtual_memory().total / (1024**3)
    
    min_requirements = {
        'ram_gb': 8,
        'cpu_cores': 4
    }
    
    issues = []
    
    # Check RAM
    if ram_gb < min_requirements['ram_gb']:
        issues.append(f"Insufficient RAM: {ram_gb:.1f}GB (minimum {min_requirements['ram_gb']}GB required)")
    
    # Check CPU
    cpu_count = psutil.cpu_count(logical=False)
    if cpu_count < min_requirements['cpu_cores']:
        issues.append(f"Insufficient CPU cores: {cpu_count} (minimum {min_requirements['cpu_cores']} required)")
    
    # Check GPU if torch is available
    if TORCH_AVAILABLE:
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"GPU detected: {gpu_name} with {vram_gb:.1f}GB VRAM")
        else:
            print("No GPU detected, will use CPU only mode")
    
    return issues

def check_requirements():
    """Check if required tools are installed"""
    requirements = {
        'ollama': {
            'windows': 'Download from https://ollama.ai/download',
            'darwin': 'brew install ollama',
            'linux': 'curl https://ollama.ai/install.sh | sh'
        },
        'python': 'Already installed',
        'git': {
            'windows': 'https://git-scm.com/download/win',
            'darwin': 'brew install git',
            'linux': 'sudo apt-get install git'
        },
        'docker': {
            'windows': 'https://docs.docker.com/desktop/windows/install/',
            'darwin': 'https://docs.docker.com/desktop/mac/install/',
            'linux': 'https://docs.docker.com/engine/install/'
        }
    }
    
    system = platform.system().lower()
    missing = []
    
    # Check Ollama
    try:
        subprocess.run(['ollama', '--version'], capture_output=True)
    except FileNotFoundError:
        missing.append(('ollama', requirements['ollama'][system]))
    
    # Check Git
    try:
        subprocess.run(['git', '--version'], capture_output=True)
    except FileNotFoundError:
        missing.append(('git', requirements['git'][system]))
    
    return missing

def setup_environment():
    """Set up Python virtual environment and install dependencies"""
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"Error: Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    # Create virtual environment
    venv_name = 'llm_env'
    subprocess.run([sys.executable, '-m', 'venv', venv_name])
    
    # Get the correct pip path
    if platform.system() == 'Windows':
        pip_path = os.path.join(venv_name, 'Scripts', 'pip')
    else:
        pip_path = os.path.join(venv_name, 'bin', 'pip')
    
    # Upgrade pip
    subprocess.run([pip_path, 'install', '--upgrade', 'pip'])
    
    # Install dependencies with platform-specific requirements
    requirements_file = Path('requirements.txt')
    subprocess.run([pip_path, 'install', '-r', str(requirements_file)])
    
    # Create .env file if not exists
    env_file = Path('.env')
    if not env_file.exists():
        default_env = f"""OLLAMA_HOST=http://localhost:11434
API_PORT=8000
STREAMLIT_PORT=8501
DEFAULT_MODEL=mistral
CUDA_VISIBLE_DEVICES=0
OLLAMA_GPU_LAYERS=28
OLLAMA_CPU_LAYERS=auto
OLLAMA_BATCH_SIZE=4
"""
        env_file.write_text(default_env)

def create_model_configs():
    """Create model configuration files"""
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    # Create default model configs
    default_config = {
        'mistral': {
            'hardware_requirements': {
                'minimum': {
                    'ram': 8,
                    'vram': 4,
                    'cpu_threads': 4
                },
                'recommended': {
                    'ram': 16,
                    'vram': 6,
                    'cpu_threads': 8
                }
            },
            'performance_profiles': {
                'balanced': {
                    'gpu_layers': 28,
                    'batch_size': 4
                },
                'memory_efficient': {
                    'gpu_layers': 20,
                    'batch_size': 2
                }
            }
        }
    }
    
    with open(models_dir / 'default.yaml', 'w') as f:
        import yaml
        yaml.dump(default_config, f)

def main():
    print("Setting up local LLM environment...")
    
    # Check hardware compatibility
    print("\nChecking hardware compatibility...")
    hw_issues = check_hardware_compatibility()
    if hw_issues:
        print("\nWarning: Hardware compatibility issues found:")
        for issue in hw_issues:
            print(f"- {issue}")
        proceed = input("\nDo you want to continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(1)
    
    # Check requirements
    print("\nChecking software requirements...")
    missing_reqs = check_requirements()
    if missing_reqs:
        print("\nMissing required tools:")
        for tool, install_cmd in missing_reqs:
            print(f"- {tool}: {install_cmd}")
        print("\nPlease install the missing tools and run setup again.")
        sys.exit(1)
    
    # Set up environment
    print("\nSetting up Python environment...")
    setup_environment()
    
    # Create model configurations
    print("\nCreating model configurations...")
    create_model_configs()
    
    print("\nSetup complete! To start chatting:")
    print("1. Run: ollama pull mistral")
    print("2. Run: python src/launcher.py")

if __name__ == "__main__":
    main()