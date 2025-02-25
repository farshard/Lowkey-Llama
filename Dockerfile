# syntax=docker/dockerfile:1

# Build arguments
ARG PYTHON_VERSION=3.9
ARG CUDA_VERSION=11.8.0

# Base image selection based on platform
FROM python:3.9-slim as base

# Build-time arguments
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Ollama
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        curl -fsSL https://ollama.ai/install.sh | sh; \
    fi

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$(uname -m)" = "x86_64" ]; then \
        pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/temp /app/models && \
    chown -R appuser:appuser /app/logs /app/temp /app/models && \
    mkdir -p /home/appuser/.ollama && \
    chown -R appuser:appuser /home/appuser/.ollama

# Switch to non-root user
USER appuser

# Copy launcher script
COPY src/launcher.py /app/src/

# Set environment variables
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_ORIGINS="*"
ENV OLLAMA_MODELS=/home/appuser/.ollama/models
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose ports
EXPOSE 8501 8000 11434

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start the application
CMD ["sh", "-c", "\
    ollama serve > /app/logs/ollama.log 2>&1 & \
    sleep 10 && \
    ollama pull mistral && \
    python src/launcher.py"]

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    API_PORT=8000 \
    CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all