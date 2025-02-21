# Platform-Specific Setup Guide

This guide provides detailed setup instructions for running the Local LLM Chat Interface on different operating systems.

## macOS Setup

### Intel-based Macs

1. **Install Prerequisites**:
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Python 3.8+ and Git
   brew install python@3.9 git
   
   # Install Ollama
   brew install ollama
   ```

2. **Clone and Setup**:
   ```bash
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Apple Silicon (M1/M2) Macs

1. **Install Prerequisites**:
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Python 3.8+ and Git
   brew install python@3.9 git
   
   # Install Ollama (M1/M2 optimized)
   brew install ollama
   ```

2. **Clone and Setup**:
   ```bash
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies with M1/M2 optimizations
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **M1/M2 Specific Configuration**:
   - Edit `config.json` to optimize for M1/M2:
     ```json
     {
       "hardware": {
         "cpu_threads": 8,
         "gpu_layers": 35,
         "batch_size": 8
       }
     }
     ```

### Common macOS Issues

1. **Ollama Installation**:
   - If Homebrew installation fails:
     ```bash
     # Try direct download
     curl -fsSL https://ollama.ai/download/ollama-darwin-arm64 -o ollama
     chmod +x ollama
     sudo mv ollama /usr/local/bin
     ```

2. **Port Conflicts**:
   - If ports are in use:
     ```bash
     # Check ports
     lsof -i :11434
     lsof -i :8501
     lsof -i :8000
     
     # Kill processes if needed
     kill -9 <PID>
     ```

3. **Permission Issues**:
   ```bash
   # Fix directory permissions
   sudo chown -R $(whoami) venv
   chmod -R u+w venv
   ```

## Windows Setup

1. **Install Prerequisites**:
   - Download and install Python 3.8+ from [python.org](https://www.python.org/downloads/)
   - Download and install Git from [git-scm.com](https://git-scm.com/download/win)
   - Download Ollama from [ollama.ai](https://ollama.ai/download)

2. **Clone and Setup**:
   ```cmd
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   
   # Create virtual environment
   python -m venv venv
   .\venv\Scripts\activate
   
   # Install dependencies
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Windows-Specific Issues

1. **Path Issues**:
   - Add Python to PATH:
     ```cmd
     setx PATH "%PATH%;C:\Users\YourUsername\AppData\Local\Programs\Python\Python39"
     ```

2. **Permission Issues**:
   - Run PowerShell as Administrator:
     ```powershell
     Set-ExecutionPolicy RemoteSigned
     ```

3. **Port Conflicts**:
   ```cmd
   # Check ports
   netstat -ano | findstr :11434
   netstat -ano | findstr :8501
   netstat -ano | findstr :8000
   
   # Kill processes
   taskkill /PID <PID> /F
   ```

## Linux Setup

1. **Install Prerequisites**:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -y python3.9 python3-pip git curl
   
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Clone and Setup**:
   ```bash
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Linux-Specific Issues

1. **CUDA Setup** (for NVIDIA GPUs):
   ```bash
   # Install CUDA drivers
   sudo ubuntu-drivers autoinstall
   
   # Verify installation
   nvidia-smi
   ```

2. **Permission Issues**:
   ```bash
   # Fix directory permissions
   sudo chown -R $USER:$USER .
   chmod -R u+w .
   ```

3. **Port Conflicts**:
   ```bash
   # Check ports
   sudo lsof -i :11434
   sudo lsof -i :8501
   sudo lsof -i :8000
   
   # Kill processes
   sudo kill -9 <PID>
   ```

## Docker Setup (All Platforms)

1. **Install Docker**:
   - [Docker Desktop for Windows/Mac](https://www.docker.com/products/docker-desktop)
   - Linux: `curl -fsSL https://get.docker.com | sh`

2. **Build and Run**:
   ```bash
   # Build image
   docker build -t local-llm .
   
   # Run container
   docker-compose up
   ```

### Docker-Specific Issues

1. **Resource Limits**:
   - Adjust Docker Desktop resources:
     - CPUs: 4+
     - Memory: 8GB+
     - Swap: 1GB+

2. **GPU Access**:
   - Install NVIDIA Container Toolkit (Linux):
     ```bash
     distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
     curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
     curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
     sudo apt-get update
     sudo apt-get install -y nvidia-docker2
     sudo systemctl restart docker
     ```

## Performance Optimization

### CPU-Only Systems
```json
{
  "hardware": {
    "cpu_threads": "auto",
    "gpu_layers": 0,
    "batch_size": 1
  }
}
```

### GPU Systems
```json
{
  "hardware": {
    "gpu_layers": 35,
    "batch_size": 8,
    "cpu_threads": 8
  }
}
```

### Low Memory Systems
```json
{
  "hardware": {
    "gpu_layers": 20,
    "batch_size": 2,
    "cpu_threads": 4
  }
}
```

## Troubleshooting Checklist

1. **System Requirements**:
   - Python 3.8+
   - 8GB RAM minimum
   - 20GB free storage
   - (Optional) NVIDIA GPU with 4GB+ VRAM

2. **Common Issues**:
   - Port conflicts
   - Permission errors
   - Memory limitations
   - GPU driver issues

3. **Logs Location**:
   - Application logs: `logs/app.log`
   - Ollama logs: Check platform-specific locations
   - Docker logs: `docker-compose logs`

4. **Clean Start**:
   ```bash
   # Remove temporary files
   rm -rf temp/*
   rm -rf logs/*
   
   # Reset virtual environment
   deactivate
   rm -rf venv
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

## Support

For additional help:
1. Check the [GitHub Issues](https://github.com/voolyvex/Local-LLM/issues)
2. Join our [Discord Community](https://discord.gg/local-llm)
3. Review the [FAQ](./faq.md) 