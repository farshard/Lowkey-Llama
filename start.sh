#!/bin/bash

# Make script exit on error
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check hardware compatibility
check_hardware() {
    # Check RAM
    total_ram=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
    ram_gb=$((total_ram / 1024 / 1024))
    if [ $ram_gb -lt 8 ]; then
        echo "Warning: System has less than 8GB RAM ($ram_gb GB)"
        echo "The application may run slowly or fail to load larger models"
    fi

    # Check CPU cores
    cpu_cores=$(nproc)
    if [ $cpu_cores -lt 4 ]; then
        echo "Warning: System has less than 4 CPU cores ($cpu_cores cores)"
        echo "Performance may be limited"
    fi

    # Check for NVIDIA GPU
    if command_exists nvidia-smi; then
        echo "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    else
        echo "No NVIDIA GPU detected, will run in CPU-only mode"
    fi
}

# Function to check and install Python dependencies
setup_python() {
    local python_cmd=""
    
    # Find Python 3.8+ installation
    for cmd in python3.11 python3.10 python3.9 python3.8 python3; do
        if command_exists $cmd; then
            version=$($cmd -c 'import sys; print(sys.version_info[1])')
            if [ $version -ge 8 ]; then
                python_cmd=$cmd
                break
            fi
        fi
    done

    if [ -z "$python_cmd" ]; then
        echo "Error: Python 3.8 or higher is required"
        echo "Please install Python 3.8+ from https://www.python.org/downloads/"
        exit 1
    fi

    echo "Using Python: $($python_cmd --version)"
    return 0
}

# Function to install Ollama based on platform
install_ollama() {
    local platform=$(uname -s)
    local arch=$(uname -m)
    
    case "$platform" in
        Darwin)
            if ! command_exists brew; then
                echo "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install ollama
            ;;
        Linux)
            curl -fsSL https://ollama.ai/install.sh | sh
            ;;
        *)
            echo "Unsupported platform for automatic Ollama installation"
            echo "Please install Ollama manually from https://ollama.ai/download"
            exit 1
            ;;
    esac
}

# Function to setup virtual environment
setup_venv() {
    local python_cmd=$1
    local venv_dir="venv"
    
    if [ ! -d "$venv_dir" ]; then
        echo "Creating virtual environment..."
        $python_cmd -m venv $venv_dir
    fi

    # Activate virtual environment
    case "$(uname -s)" in
        MINGW*|CYGWIN*|MSYS*)
            source $venv_dir/Scripts/activate
            ;;
        *)
            source $venv_dir/bin/activate
            ;;
    esac

    # Upgrade pip
    python -m pip install --upgrade pip

    # Install dependencies with platform-specific considerations
    if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
        # M1/M2 Mac-specific requirements
        pip install --no-cache-dir torch==2.2.1
    fi

    # Install main requirements
    pip install -r requirements.txt
}

# Main setup process
main() {
    echo "Setting up Lowkey Llama..."
    
    # Check hardware compatibility
    echo "Checking hardware compatibility..."
    check_hardware
    
    # Setup Python
    echo "Checking Python installation..."
    setup_python
    python_cmd=$?
    
    # Check if Ollama is installed
    if ! command_exists ollama; then
        echo "Ollama is not installed. Would you like to install it? (y/n)"
        read -r answer
        if [ "$answer" = "y" ]; then
            install_ollama
        else
            echo "Please install Ollama manually from https://ollama.ai/download"
            exit 1
        fi
    fi

    # Setup virtual environment
    setup_venv $python_cmd

    # Create necessary directories
    mkdir -p logs temp models

    # Start the application
    echo "Starting Lowkey Llama..."
    python src/launcher.py
}

# Run main setup
main 