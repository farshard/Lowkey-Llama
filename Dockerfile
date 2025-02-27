# Use multi-stage build for smaller final image
FROM python:3.9-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Copy application files
WORKDIR /app
COPY requirements.txt .
COPY src/ src/
COPY models/ models/
COPY config.json .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.9-slim

# Copy from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/bin/ollama /usr/local/bin/ollama

WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p logs temp models cache && \
    chmod -R 755 logs temp models cache

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:11434 || exit 1

# Entry point script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]