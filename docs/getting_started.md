# Getting Started with Local LLM Chat Interface

This guide will help you set up and run Lowkey Llama on your system.

## Hardware Requirements

### Minimum Requirements
- CPU: 4 cores, 8 threads
- RAM: 8GB
- Storage: 20GB free space
- GPU: Optional, but recommended (4GB+ VRAM)

### Recommended Requirements
- CPU: 8+ cores, 16+ threads
- RAM: 16GB+
- Storage: 50GB+ free space
- GPU: 8GB+ VRAM (NVIDIA RTX 3060 or better)

## Hardware Compatibility Profiles

The system automatically detects your hardware capabilities and selects the appropriate profile:

1. **High VRAM (8GB+)**
   - Full GPU acceleration
   - Maximum batch size
   - Parallel model loading
   - Suitable for all models

2. **Medium VRAM (6-8GB)**
   - Balanced GPU/CPU split
   - Reduced batch size
   - Limited parallel loading
   - Suitable for most models with optimization

3. **Low VRAM (4-6GB)**
   - Heavy CPU offloading
   - Minimal batch size
   - No parallel loading
   - Limited to smaller models

4. **CPU Only (<4GB or no GPU)**
   - Full CPU computation
   - Minimal memory usage
   - Longer processing times
   - Limited to basic models

## Model Compatibility

### Mistral (7B)
- VRAM Required: 4GB
- RAM Required: 8GB
- CPU Threads: 8+
- Adaptable to all profiles

### CodeLlama
- 13B Variant:
  - VRAM Required: 5GB
  - RAM Required: 16GB
  - CPU Threads: 8+
  - Works with medium/high VRAM profiles
- 34B Variant:
  - VRAM Required: 8GB
  - RAM Required: 32GB
  - CPU Threads: 16+
  - Requires high VRAM profile or heavy CPU offloading

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
   git clone https://github.com/farshard/Lowkey-Llama.git
   cd Lowkey-Llama
   ```

2. Create a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   # Windows
   python -m pip install -r requirements.txt
   
   # macOS/Linux
   pip install -r requirements.txt
   ```

### Method 2: Docker Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/farshard/Lowkey-Llama.git
   cd Lowkey-Llama
   ```

2. Use the Docker management script:
   ```bash
   # Windows
   docker.bat start
   
   # macOS/Linux
   chmod +x docker.sh
   ./docker.sh start
   ```

3. Configuration:
   The script automatically creates a `.env` file with default settings.
   You can modify these settings:
   ```env
   PYTHON_VERSION=3.9
   CUDA_VERSION=11.8.0
   OLLAMA_PORT=11434
   UI_PORT=8501
   API_PORT=8002
   ```

4. Accessing the Application:
   - Web UI: http://localhost:8501
   - API Documentation: http://localhost:8002/docs
   - Ollama API: http://localhost:11434

## Configuration

1. Environment Variables:
   Create a `.env` file in the root directory:
   ```env
   OLLAMA_HOST=http://localhost:11434
   API_PORT=8002
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
   # Windows
   python src\chat_app.py
   
   # macOS/Linux
   python3 src/chat_app.py
   ```
2. Open your browser at `http://localhost:8501`

### API Server

1. Start the FastAPI server:
   ```bash
   # Windows
   python src\api_server.py
   
   # macOS/Linux
   python3 src/api_server.py
   ```
2. Access the API documentation at `http://localhost:8002/docs`

## Performance Optimization

### GPU Optimization
- Monitor VRAM usage with task manager
- Adjust GPU layers if needed
- Consider using smaller models for better performance

### CPU Optimization
- Set appropriate thread count
- Monitor CPU usage
- Adjust batch size based on load

### Memory Management
- Use appropriate storage locations
- Monitor RAM usage
- Clear cache if needed

## Troubleshooting

### Common Issues
1. **Out of VRAM**
   - Reduce GPU layers
   - Switch to a smaller model
   - Enable CPU offloading

2. **Slow Performance**
   - Check hardware compatibility
   - Adjust batch size
   - Consider different model variant

3. **Memory Errors**
   - Clear model cache
   - Reduce batch size
   - Check available RAM

4. **Path Issues**
   - Windows: Use backslashes in paths
   - macOS/Linux: Use forward slashes
   - Use `os.path.join()` in Python code

5. **Permission Issues**
   - Windows: Run as Administrator if needed
   - macOS/Linux: Use `chmod +x` for scripts
   - Check file ownership with `ls -l`

6. **Python Command**
   - Windows: Use `python`
   - macOS/Linux: Use `python3`
   - Set correct PATH environment variable

7. **Port Conflicts**
   ```bash
   # Windows
   netstat -ano | findstr :8002
   
   # macOS/Linux
   lsof -i :8002
   ```

## Next Steps

- Read the [API Documentation](api.md) for integrating with other applications
- Check [Model Configuration](../models/README.md) for customizing model behavior
- See [Development Guide](development.md) for contributing to the project

## Testing Your Models

### Testing for Hallucinations

It's important to validate that your models provide accurate, factual responses. Here's how to test for hallucinations:

1. Using the API directly:
   ```bash
   # Test with future predictions
   curl -X POST "http://localhost:8002/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "mistral-factual",
       "prompt": "What will be the dominant programming language in 2030?",
       "temperature": 0.5
     }'

   # Test with complex scientific questions
   curl -X POST "http://localhost:8002/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "mistral-factual",
       "prompt": "What is dark matter made of at the quantum level?",
       "temperature": 0.5
     }'
   ```

2. Key aspects to test:
   - Future predictions (model should express uncertainty)
   - Scientific facts (model should acknowledge current limitations in knowledge)
   - Recent events (model should clarify knowledge cutoff)
   - Complex topics (model should distinguish between facts and theories)

3. Evaluating responses:
   - Look for explicit acknowledgment of uncertainty
   - Check for clear distinction between facts and speculation
   - Verify that the model admits when it doesn't have enough information
   - Ensure responses include appropriate caveats and limitations 