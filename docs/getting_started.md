# Getting Started with Local LLM Chat Interface

This guide will help you set up and run the Local LLM Chat Interface on your system.

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **Ollama**
   - Download from [ollama.ai](https://ollama.ai)
   - Verify installation:
     ```bash
     ollama --version
     ```

3. **Docker** (optional)
   - Required only if you plan to use containerized deployment
   - Download from [docker.com](https://www.docker.com/get-started)

## Installation

### Method 1: Direct Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t local-llm .
   ```

2. Run using docker-compose:
   ```bash
   docker-compose up
   ```

## Configuration

1. Environment Variables:
   Create a `.env` file in the root directory:
   ```env
   OLLAMA_HOST=http://localhost:11434
   API_PORT=8000
   STREAMLIT_PORT=8501
   DEFAULT_MODEL=mistral
   ```

2. Model Configuration:
   - See the `models/` directory for model-specific configurations
   - Default model settings are in `models/default.yaml`

## Running the Application

### Chat Interface

1. Start the Streamlit interface:
   ```bash
   streamlit run src/chat_app.py
   ```
2. Open your browser at `http://localhost:8501`

### API Server

1. Start the FastAPI server:
   ```bash
   python src/api_server.py
   ```
2. Access the API documentation at `http://localhost:8000/docs`

## Common Issues and Solutions

1. **Ollama Connection Error**
   - Ensure Ollama is running: `ollama run mistral`
   - Check if the correct host is configured in `.env`

2. **Port Conflicts**
   - Change ports in `.env` if 8000 or 8501 are in use
   - Restart the application after changing ports

3. **Model Loading Issues**
   - Verify model is downloaded: `ollama list`
   - Check model configuration in `models/` directory

## Next Steps

- Read the [API Documentation](api.md) for integrating with other applications
- Check [Model Configuration](../models/README.md) for customizing model behavior
- See [Development Guide](development.md) for contributing to the project 