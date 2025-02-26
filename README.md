# Local LLM Chat Interface

A streamlined interface for interacting with local language models through Ollama.

## Quick Start

1. **Prerequisites**
   - Python 3.8 or higher
   - [Ollama](https://ollama.ai/download) installed
   - Windows or macOS

2. **Installation**
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/Local-LLM.git
   cd Local-LLM

   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate     # On Windows

   # Install dependencies
   python -m pip install -r requirements.txt
   ```

3. **Running the Application**
   ```bash
   python src/launcher.py
   ```

The launcher will:
1. Check and install dependencies
2. Verify Ollama installation and pull required models
3. Start the API server (default port 8000, falls back to 8001-8005 if needed)
4. Launch the Streamlit UI
5. Open your default browser automatically

## System Requirements

- **Hardware**
  - Minimum 8GB RAM
  - 4+ CPU cores
  - GPU recommended but not required

- **Software**
  - Python 3.8+
  - Ollama 0.5.0+
  - Windows 10/11 or macOS 10.15+

- **Network**
  - The system dynamically manages ports:
    - API server: starts on 8000, falls back to 8001-8005 if needed
    - UI server: starts on 8501, falls back to 8502-8505 if needed
    - Ollama: uses 11434 (must be available)
  - The config.json is automatically updated with the actual ports being used

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Error: "Port X is already in use"
   - Solutions:
     1. The system will automatically try fallback ports
     2. Check the console output for the actual ports being used
     3. The config.json file will be updated with the working ports
     4. Restart your computer if ports are held by zombie processes

2. **API Connection Issues**
   - Error: "API request failed: 404 Not Found"
   - Solutions:
     1. The UI automatically uses the port from config.json
     2. If you see this error, restart the application
     3. The system will find available ports and update the configuration
     4. If issues persist, try: `taskkill /F /IM python.exe` (Windows) or `pkill python` (macOS/Linux)

2. **Ollama Issues**
   - Error: "Failed to start Ollama server"
   - Solutions:
     1. Ensure Ollama is installed and in PATH
     2. Run `ollama serve` manually to check for errors
     3. Check Ollama logs for detailed information

3. **Dependency Issues**
   - Error: "Failed to install dependencies"
   - Solutions:
     1. Update pip: `python -m pip install --upgrade pip`
     2. Install manually: `pip install -r requirements.txt`
     3. Check Python version compatibility

4. **Model Download Issues**
   - Error: "Failed to pull model"
   - Solutions:
     1. Check internet connection
     2. Ensure sufficient disk space
     3. Try pulling model manually: `ollama pull mistral`

### Advanced Troubleshooting

1. **Check System Status**
   ```bash
   # Check Ollama status
   curl http://localhost:11434/api/health

   # List running Python processes
   ps aux | grep python    # macOS/Linux
   tasklist | findstr python.exe  # Windows

   # Check port usage
   netstat -ano | findstr :8000   # Windows
   lsof -i :8000                  # macOS/Linux
   ```

2. **Clean Start**
   ```bash
   # Stop all related processes
   taskkill /F /IM ollama.exe    # Windows
   pkill ollama                  # macOS/Linux

   # Clear temporary files
   rm -rf src/temp_audio/*

   # Restart application
   python src/launcher.py
   ```

## Development

See [development.md](docs/development.md) for:
- Project structure
- Development setup
- Testing guidelines
- Contributing instructions

## Architecture

The system uses a modular architecture with these main components:

1. **System Orchestrator**
   - Manages initialization and shutdown
   - Coordinates all components
   - Handles dependency checks

2. **API Server**
   - FastAPI backend
   - Handles model interactions
   - Manages audio processing

3. **Streamlit UI**
   - User interface
   - Real-time chat
   - Settings management

4. **Ollama Integration**
   - Model management
   - Inference handling
   - Server lifecycle

For detailed API documentation, see [api.md](docs/api.md).

## License

MIT License - See LICENSE file for details.
