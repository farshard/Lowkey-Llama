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
│   └── setup.py         # Package setup
├── tests/               # Test suite
│   ├── test_api.py
│   └── test_chat.py
├── docs/                # Documentation
├── models/              # Model configurations
├── requirements.txt     # Production dependencies
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