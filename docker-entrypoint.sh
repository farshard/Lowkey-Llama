#!/bin/bash
set -e

# Function to check hardware and set environment variables
check_hardware() {
    # Check for NVIDIA GPU
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
        
        # Get GPU memory in MB
        gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
        
        # Set environment variables based on GPU memory
        if [ "$gpu_memory" -ge 8000 ]; then
            export OLLAMA_GPU_LAYERS=35
            export OLLAMA_BATCH_SIZE=8
            export OLLAMA_THREAD_COUNT=auto
        elif [ "$gpu_memory" -ge 6000 ]; then
            export OLLAMA_GPU_LAYERS=28
            export OLLAMA_BATCH_SIZE=4
            export OLLAMA_THREAD_COUNT=16
        else
            export OLLAMA_GPU_LAYERS=20
            export OLLAMA_BATCH_SIZE=2
            export OLLAMA_THREAD_COUNT=8
        fi
    else
        echo "No NVIDIA GPU detected, running in CPU-only mode"
        export OLLAMA_GPU_LAYERS=0
        export OLLAMA_CPU_LAYERS=all
        export OLLAMA_BATCH_SIZE=1
        export OLLAMA_THREAD_COUNT=auto
    fi
}

# Set up environment
setup_environment() {
    # Set default environment variables
    export PYTHONUNBUFFERED=1
    export STREAMLIT_SERVER_PORT=${STREAMLIT_SERVER_PORT:-8501}
    export API_PORT=${API_PORT:-8000}
    export OLLAMA_HOST=${OLLAMA_HOST:-0.0.0.0}
    export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    
    # Create log directory if it doesn't exist
    mkdir -p /app/logs
}

# Start Ollama service
start_ollama() {
    echo "Starting Ollama service..."
    nohup ollama serve > /app/logs/ollama.log 2>&1 &
    
    # Wait for Ollama to start
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/health >/dev/null; then
            echo "Ollama service is ready"
            break
        fi
        echo "Waiting for Ollama service... ($i/30)"
        sleep 1
    done
    
    # Pull required model
    echo "Pulling Mistral model..."
    ollama pull mistral
}

# Start API server
start_api() {
    echo "Starting API server..."
    nohup uvicorn src.api_server:app --host 0.0.0.0 --port ${API_PORT} > /app/logs/api.log 2>&1 &
    
    # Wait for API to start
    for i in {1..30}; do
        if curl -s http://localhost:${API_PORT}/health >/dev/null; then
            echo "API server is ready"
            break
        fi
        echo "Waiting for API server... ($i/30)"
        sleep 1
    done
}

# Main function
main() {
    setup_environment
    check_hardware
    start_ollama
    start_api
    
    echo "Starting Streamlit UI..."
    exec streamlit run src/chat_app.py \
        --server.address 0.0.0.0 \
        --server.port ${STREAMLIT_SERVER_PORT} \
        --server.headless true
}

# Run main function
main 