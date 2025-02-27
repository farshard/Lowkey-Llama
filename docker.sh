#!/bin/bash
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check hardware compatibility
check_hardware() {
    echo "Checking hardware compatibility..."
    
    # Check RAM
    if command_exists free; then
        total_ram=$(free -g | awk '/^Mem:/{print $2}')
        if [ "$total_ram" -lt 8 ]; then
            echo "Warning: System has less than 8GB RAM (${total_ram}GB)"
            echo "The application may run slowly or fail to load larger models"
        fi
    fi

    # Check CPU cores
    if command_exists nproc; then
        cpu_cores=$(nproc)
        if [ "$cpu_cores" -lt 4 ]; then
            echo "Warning: System has less than 4 CPU cores ($cpu_cores cores)"
            echo "Performance may be limited"
        fi
    fi

    # Check for NVIDIA GPU and set profile
    if command_exists nvidia-smi; then
        echo "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
        gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
        
        # Set profile based on GPU memory
        if [ "$gpu_memory" -ge 8000 ]; then
            echo "Using high-VRAM profile"
            echo "OLLAMA_GPU_LAYERS=35" >> .env
            echo "OLLAMA_BATCH_SIZE=8" >> .env
            profile="gpu-high"
        elif [ "$gpu_memory" -ge 6000 ]; then
            echo "Using medium-VRAM profile"
            echo "OLLAMA_GPU_LAYERS=28" >> .env
            echo "OLLAMA_BATCH_SIZE=4" >> .env
            profile="gpu-medium"
        else
            echo "Using low-VRAM profile"
            echo "OLLAMA_GPU_LAYERS=20" >> .env
            echo "OLLAMA_BATCH_SIZE=2" >> .env
            profile="gpu-low"
        fi
    else
        echo "No NVIDIA GPU detected, using CPU-only profile"
        echo "OLLAMA_GPU_LAYERS=0" >> .env
        echo "OLLAMA_CPU_LAYERS=all" >> .env
        echo "OLLAMA_BATCH_SIZE=1" >> .env
        profile="cpu"
    fi
}

# Function to check Docker installation
check_docker() {
    if ! command_exists docker; then
        echo "Error: Docker is not installed"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command_exists docker-compose; then
        echo "Error: docker-compose is not installed"
        echo "Please install docker-compose from https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    mkdir -p logs temp models cache
    
    # Set up .env file if it doesn't exist
    if [ ! -f .env ]; then
        echo "Creating default .env file..."
        cat > .env << EOL
PYTHON_VERSION=3.9
CUDA_VERSION=11.8.0
OLLAMA_PORT=11434
UI_PORT=8501
API_PORT=8000
EOL
    fi
}

# Function to start services
start_services() {
    echo "Starting Lowkey Llama with Docker..."
    check_docker
    check_hardware
    create_directories
    
    echo "Building Docker images..."
    docker-compose build
    
    echo "Starting services with $profile profile..."
    docker-compose --profile $profile up -d
    
    echo "Services started. Use './docker.sh logs' to view logs"
}

# Function to stop services
stop_services() {
    echo "Stopping Lowkey Llama services..."
    docker-compose down
}

# Function to restart services
restart_services() {
    stop_services
    start_services
}

# Function to view logs
view_logs() {
    docker-compose logs -f
}

# Function to show status
show_status() {
    echo "Lowkey Llama Container Status:"
    docker-compose ps
}

# Function to show help
show_help() {
    echo "Lowkey Llama Docker Management Script"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start     Start all services"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show container status"
    echo "  logs      View logs from all services"
    echo "  help      Show this help message"
}

# Main script
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        view_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -z "$1" ]; then
            start_services
        else
            echo "Unknown command: $1"
            echo
            show_help
            exit 1
        fi
        ;;
esac 