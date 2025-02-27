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

1. Clone the repository:
   ```bash
   git clone https://github.com/voolyvex/Local-LLM.git
   cd Local-LLM
   ```

2. Use the Docker management script:
   ```bash
   # Make the script executable (Unix/MacOS)
   chmod +x docker.sh
   
   # Start the application
   ./docker.sh start
   
   # View available commands
   ./docker.sh help
   ```

   The script provides the following commands:
   - `start`: Start all services
   - `stop`: Stop all services
   - `restart`: Restart all services
   - `status`: Show container status
   - `logs`: View logs from all services

3. Hardware-Based Profiles:
   The script automatically detects your hardware and selects the appropriate profile:
   - `gpu-high`: For GPUs with 8GB+ VRAM
   - `gpu-medium`: For GPUs with 6-8GB VRAM
   - `gpu-low`: For GPUs with <6GB VRAM
   - `cpu`: For systems without GPU

4. Configuration:
   The script automatically creates a `.env` file with default settings.
   You can modify these settings:
   ```env
   PYTHON_VERSION=3.9
   CUDA_VERSION=11.8.0
   OLLAMA_PORT=11434
   UI_PORT=8501
   API_PORT=8000
   ```

   GPU-specific settings are automatically configured based on your hardware:
   ```env
   OLLAMA_GPU_LAYERS=35    # Varies by profile
   OLLAMA_BATCH_SIZE=8     # Varies by profile
   OLLAMA_CPU_LAYERS=all   # For CPU-only mode
   ```

5. Accessing the Application:
   - Web UI: http://localhost:8501
   - API Documentation: http://localhost:8000/docs
   - Ollama API: http://localhost:11434

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

## Next Steps

- Read the [API Documentation](api.md) for integrating with other applications
- Check [Model Configuration](../models/README.md) for customizing model behavior
- See [Development Guide](development.md) for contributing to the project 