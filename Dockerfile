# syntax=docker/dockerfile:1

# Build arguments
ARG PYTHON_VERSION=3.9
ARG CUDA_VERSION=11.8.0

# Base image selection based on platform
FROM --platform=$BUILDPLATFORM python:${PYTHON_VERSION}-slim as builder

# Build-time arguments
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install platform-specific dependencies
RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        curl -fsSL https://ollama.ai/install.sh | sh; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        curl -fsSL https://ollama.ai/install.sh | sh; \
    fi

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with platform-specific considerations
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        pip install torch==2.2.1+cu118 -f https://download.pytorch.org/whl/cu118/torch_stable.html; \
    elif [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        pip install torch==2.2.1; \
    fi

# Copy application files
COPY . .

# Create non-root user and set permissions
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create necessary directories
RUN mkdir -p /app/logs /app/temp /app/models && \
    chown -R appuser:appuser /app/logs /app/temp /app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501 || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    API_PORT=8000 \
    OLLAMA_HOST=http://localhost:11434 \
    CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all

# Expose ports (Streamlit:8501, API:8000)
EXPOSE 8501 8000

# Copy the launcher script
COPY src/launcher.py /app/src/

# Start script with platform-specific optimizations
CMD ["python", "-u", "src/launcher.py"] 