# Development Guide

This guide provides information for developers who want to contribute to the Lowkey Llama project.

## Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/Local-LLM.git
   cd Local-LLM
   ```

2. **Create Development Environment**
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

## Project Structure

```
.
├── src/                  # Source code
│   ├── chat_app.py      # Streamlit interface
│   ├── api_server.py    # FastAPI server
│   ├── launcher.py      # Application launcher
│   ├── ollama_server.py # Ollama service manager
│   └── core/            # Core functionality
│       ├── config.py    # Configuration management
│       ├── ui.py        # UI components
│       └── ollama.py    # Ollama client
├── tests/               # Test suite
│   ├── test_api.py
│   ├── test_chat.py
│   └── test_ollama.py
├── docs/                # Documentation
│   ├── getting_started.md
│   ├── development.md
│   └── api.md
├── models/              # Model configurations
├── docker/             # Docker configuration
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── docker-compose.yml
├── scripts/            # Management scripts
│   ├── docker.sh      # Docker management
│   ├── start.sh       # Unix startup
│   └── start.bat      # Windows startup
├── logs/               # Log files
├── cache/             # Cache directory
├── temp/              # Temporary files
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## Coding Standards

1. **Python Style Guide**
   - Follow PEP 8 style guide
   - Use type hints (PEP 484)
   - Maximum line length: 88 characters (Black formatter)

2. **Documentation**
   - Write docstrings for all public functions (Google style)
   - Keep README.md up to date
   - Document API changes

3. **Testing**
   - Write unit tests for new features
   - Maintain test coverage above 80%
   - Use pytest for testing

## Git Workflow

1. **Branching Strategy**
   - `main`: Production-ready code
   - `develop`: Development branch
   - Feature branches: `feature/your-feature`
   - Bug fixes: `fix/bug-description`

2. **Commit Messages**
   Follow conventional commits:
   ```
   feat: add new feature
   fix: resolve bug
   docs: update documentation
   test: add tests
   refactor: code improvement
   ```

3. **Pull Requests**
   - Create PR against `develop` branch
   - Fill out PR template
   - Request review from maintainers

## Testing

1. **Running Tests**
   ```bash
   pytest
   pytest --cov=src tests/  # With coverage
   ```

2. **Test Structure**
   ```python
   def test_feature():
       # Arrange
       input_data = ...
       
       # Act
       result = function_under_test(input_data)
       
       # Assert
       assert result == expected_output
   ```

## Adding New Features

1. **Planning**
   - Create an issue describing the feature
   - Discuss implementation approach
   - Get approval from maintainers

2. **Implementation**
   - Create feature branch
   - Implement feature with tests
   - Update documentation
   - Submit PR

3. **Review Process**
   - Address review comments
   - Update tests if needed
   - Squash commits if requested

## Debugging Tips

1. **Logging**
   ```python
   import logging
   
   logging.debug("Debug message")
   logging.info("Info message")
   logging.error("Error message")
   ```

2. **Debugging Tools**
   - Use `pdb` or `ipdb` for debugging
   - VS Code debugging configuration provided

## Performance Optimization

1. **Profiling**
   ```bash
   python -m cProfile -o output.prof src/your_script.py
   snakeviz output.prof  # Visualize profile
   ```

2. **Best Practices**
   - Use async/await for I/O operations
   - Implement caching where appropriate
   - Monitor memory usage

## Release Process

1. **Version Bump**
   - Update version in `setup.py`
   - Update CHANGELOG.md
   - Create release branch

2. **Testing**
   - Run full test suite
   - Perform manual testing
   - Check documentation

3. **Release**
   - Merge to main
   - Create GitHub release
   - Update Docker images

## Getting Help

- Join our Discord community
- Check existing issues
- Create detailed bug reports
- Ask questions in discussions

Remember to always write clean, maintainable code and follow the project's conventions!

## Docker Development

### Docker Files
```
.
├── Dockerfile              # Main container definition
├── docker-entrypoint.sh   # Container startup script
├── docker.sh              # Host-side management script
└── docker-compose.yml     # Service orchestration
```

### Docker Profiles
The system supports different hardware profiles through Docker Compose:

1. **High VRAM Profile** (`gpu-high`)
   ```yaml
   environment:
     - OLLAMA_GPU_LAYERS=35
     - OLLAMA_BATCH_SIZE=8
     - OLLAMA_THREAD_COUNT=auto
   ```

2. **Medium VRAM Profile** (`gpu-medium`)
   ```yaml
   environment:
     - OLLAMA_GPU_LAYERS=28
     - OLLAMA_BATCH_SIZE=4
     - OLLAMA_THREAD_COUNT=16
   ```

3. **Low VRAM Profile** (`gpu-low`)
   ```yaml
   environment:
     - OLLAMA_GPU_LAYERS=20
     - OLLAMA_BATCH_SIZE=2
     - OLLAMA_THREAD_COUNT=8
   ```

4. **CPU Profile** (`cpu`)
   ```yaml
   environment:
     - OLLAMA_GPU_LAYERS=0
     - OLLAMA_CPU_LAYERS=all
     - OLLAMA_BATCH_SIZE=1
     - OLLAMA_THREAD_COUNT=auto
   ```

### Docker Development Workflow

1. **Building Images**
   ```bash
   ./docker.sh start
   ```

2. **Testing Changes**
   ```bash
   # View logs
   ./docker.sh logs
   
   # Restart services
   ./docker.sh restart
   
   # Check status
   ./docker.sh status
   ```

3. **Debugging**
   - Check container logs: `docker-compose logs -f [service]`
   - Shell into container: `docker-compose exec lowkey-llama bash`
   - View resource usage: `docker stats`

4. **Best Practices**
   - Use multi-stage builds to minimize image size
   - Keep base images updated
   - Follow the principle of least privilege
   - Use health checks
   - Implement proper logging
   - Handle signals correctly 