<p align="center">
  <img src="assets/lowkey-logo-pnk-775.png" alt="Lowkey Llama" width="400"/>
</p>

<h3 align="center">A personal interface for interacting with local language models through Ollama</h3>

> 🔒 **Privacy Statement**: Everything runs locally on your machine. No cloud services, no data collection, no external dependencies. Your conversations and data stay completely private.

## Quick Start

1. **Prerequisites**
   - Python 3.8 or higher
   - [Ollama](https://ollama.ai/download) installed
   - Windows or macOS

2. **Installation**
   ```bash
   # Clone the repository
   git clone https://github.com/farshard/Lowkey-Llama.git
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
3. Start the API server (port 8002)
4. Launch the Streamlit UI (port 8501)
5. Open your default browser automatically

## Custom Models

This application supports creating and using custom models with optimized parameters:

1. **Using Pre-configured Models**
   - `mistral-factual`: Optimized for accurate, format-compliant responses
     - Ultra-low temperature (0.01) for deterministic outputs
     - Strict format enforcement with zero tolerance
     - Specialized for exact word count requirements
   - `mistral-format`: Optimized for precise formatting
     - Extremely focused sampling (top-p: 0.1)
     - Minimal token selection (top-k: 3)
     - Format-first approach with strict verification

2. **Creating Your Own Models**
   ```bash
   # Create a custom model using a modelfile
   ollama create my-custom-model -f models/my-custom-model.modelfile
   ```

3. **Model Optimization**
   - See [custom_models.md](docs/custom_models.md) for detailed instructions on:
     - Creating custom models with specialized capabilities
     - Optimizing parameters for different use cases
     - Troubleshooting model issues
     - Example modelfiles for different purposes

4. **Adding to Configuration**
   - Custom models are automatically detected
   - You can add them to `config.json` for persistent settings:
   ```json
   "models": {
       "mistral-factual": {
           "temp": 0.01,
           "top_p": 0.1,
           "top_k": 3,
           "max_tokens": 4096,
           "context_window": 8192
       }
   }
   ```

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
  - Fixed port configuration:
    - API server: port 8002
    - UI server: port 8501
    - Ollama: port 11434 (must be available)
  - The launcher automatically handles port cleanup and management

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

### Short or Truncated Responses from Mistral

If you're getting very short (one-word) responses from Mistral models, try these solutions:

1. Use the `mistral-fixed` model (recommended):
   ```bash
   # Create the optimized model
   ollama create mistral-fixed -f models/mistral-fixed.modelfile
   
   # Then select "mistral-fixed" in the model dropdown
   ```

2. The `mistral-fixed` model includes:
   - Optimized parameters for detailed responses
   - Enhanced system prompt forcing comprehensive answers
   - Improved handling of the Ollama API's ndjson format
   - Better fallback mechanisms for incomplete responses

3. Adjust settings in the UI:
   - Increase temperature (0.7-0.9) for more detailed responses
   - Set max tokens higher (2048+) to allow for longer outputs
   - Use the "mistral-fixed" model which is pre-configured for verbosity

4. Be explicit in your prompts:
   - Add phrases like "Please provide a detailed answer with multiple paragraphs"
   - Ask for explanations: "Explain in detail..."
   - Request specific number of examples or points

5. For developers, see [custom_models.md](docs/custom_models.md) for:
   - How to create custom models with specific optimization parameters
   - Troubleshooting model response issues
   - Advanced configuration options

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
