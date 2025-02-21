# Use official Python base image
FROM python:3.9-slim

# Install system dependencies and Ollama
RUN apt-get update && apt-get install -y \
    curl \
    && curl https://ollama.ai/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose ports (Ollama:11434, Streamlit:8501, API:8000)
EXPOSE 11434 8501 8000

# Start script
CMD ["sh", "-c", "nohup ollama serve & sleep 5 && streamlit run src/chat_app.py"] 