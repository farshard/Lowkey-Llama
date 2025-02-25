# Local LLM Chat Interface 🤖

A private server and web UI for running local language models through Ollama, with API access.

<img src="https://github.com/user-attachments/assets/a3e0426a-74af-41a1-bd09-fd2d82a56a22" alt="image" width="80%">
<p align="center"><i>Streamlit interface</i></p>


## Quick Start 🚀

### Using Docker (Recommended)
```bash
# Pull and run with one command
docker run -d --name local-llm \
  -p 8501:8501 -p 8000:8000 \
  --gpus all \  # Optional: for GPU support
  voolyvex/local-llm:latest

# Or build and run locally
git clone https://github.com/voolyvex/Local-LLM.git
cd Local-LLM
docker compose up -d

# ☝️ Docker must be running for commands to work
```

### Manual Setup
1. **Prerequisites**:
   - Python 3.8+
   - [Ollama](https://ollama.ai/download)

2. **Install & Run**:
   ```bash
   # Clone and setup
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   python -m venv venv

   # Activate virtual environment
   # Windows:           # macOS/Linux:
   .\venv\Scripts\activate    # source venv/bin/activate

   # Install and launch
   pip install -r requirements.txt
   python src/launcher.py
   ```

3. Open `http://localhost:8501` in your browser

## System Requirements

- Minimum: 8GB RAM, 4 CPU cores
- Recommended: 16GB+ RAM, 8+ CPU cores, NVIDIA GPU (8GB+ VRAM)

## Features

- Web interface with Streamlit
- REST API for integration
- Text-to-Speech support
- Multiple model support (Mistral, CodeLlama, Mixtral)

## Architecture

```mermaid
C4Context
title Local LLM Chat Interface - System Architecture

Person(user, "User", "Interacts with the chat interface")

Boundary(app, "Local LLM Chat Interface") {
    System(web_ui, "Web Interface", "Streamlit-based chat UI")
    System(api, "API Server", "FastAPI REST endpoints")
    System(launcher, "Service Launcher", "Manages services and configuration")
}

System_Ext(ollama, "Ollama Service", "Local model server")
ContainerDb(models, "Local Models", "Downloaded LLM models")

Rel(user, web_ui, "Interacts via browser")
Rel(user, api, "Makes API calls")
Rel(web_ui, api, "Sends requests")
Rel(api, ollama, "Manages model interactions")
Rel(ollama, models, "Loads and runs")
Rel(launcher, web_ui, "Starts and monitors")
Rel(launcher, api, "Starts and monitors")
Rel(launcher, ollama, "Starts and monitors")
```

## Documentation

- [Platform Setup Guide](docs/platform_setup.md)
- [API Documentation](docs/api.md)
- [Troubleshooting](docs/platform_setup.md#troubleshooting-checklist)



## License

MIT License - see [LICENSE](LICENSE) file
