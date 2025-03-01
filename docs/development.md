# Development Guide

This guide provides information specific to developing Lowkey Llama.

## Project Structure

```
.
├── src/                  # Source code
│   ├── chat_app.py      # Streamlit interface
│   ├── api_server.py    # FastAPI server (port 8002)
│   ├── launcher.py      # Application launcher
│   ├── ollama_server.py # Ollama service manager
│   └── core/            # Core functionality
│       ├── config.py    # Configuration management
│       ├── ui.py        # UI components
│       └── ollama.py    # Ollama client
├── tests/               # Test suite
├── docs/                # Documentation
├── models/              # Model configurations
└── requirements.txt     # Dependencies
```

## Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/farshard/Lowkey-Llama.git
   cd Lowkey-Llama
   ```

2. **Create Development Environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Testing

1. **Running Tests**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=src tests/
   ```

2. **Test Categories**
   - API endpoint tests
   - Model interaction tests
   - Configuration tests
   - UI component tests

## Adding New Models

1. Create a new modelfile in `models/`:
   ```
   FROM base-model
   
   PARAMETER temperature 0.7
   ...
   ```

2. Add model configuration to `config.json`:
   ```json
   "models": {
     "new-model": {
       "temp": 0.7,
       "max_tokens": 4096
     }
   }
   ```

3. Test the model using the provided test suite:
   ```bash
   pytest tests/test_models.py -k "test_new_model"
   ```

## Platform-Specific Development

### Windows
- Use `start.bat` for launching
- Set `PYTHONPATH` to include project root
- Use `python` command (not `python3`)

### macOS/Linux
- Make scripts executable: `chmod +x *.sh`
- Use `./start.sh` for launching
- Use `python3` command
- Set correct file permissions

### Docker Development
- Use provided Docker profiles based on hardware
- Test builds on all target platforms
- Verify port mappings and volume mounts

## Performance Optimization

1. **Model-Specific Settings**
   ```json
   {
     "hardware": {
       "cpu_threads": "auto",
       "gpu_layers": 35,
       "batch_size": 8
     }
   }
   ```

2. **Platform-Specific Tuning**
   - Windows: Adjust process priority
   - macOS: Enable hardware acceleration
   - Linux: Configure CUDA parameters

## Common Issues

1. **Port Conflicts**
   - API server (8002): Check for existing services
   - UI server (8501): Verify Streamlit ports
   - Ollama (11434): Ensure Ollama is running

2. **Model Loading**
   - Verify Ollama installation
   - Check model file permissions
   - Monitor system resources

3. **Cross-Platform**
   - Use os.path for file operations
   - Handle path separators
   - Check file permissions 