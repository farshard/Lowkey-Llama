# Model Configurations 🧠

Configuration files for language models supported by the Local LLM Chat Interface.

## Available Models

1. **Mistral (Default)**
   - General purpose, 4GB VRAM
   - Best for: Chat, writing, analysis

2. **CodeLlama**
   - Code generation specialist
   - 13B: 5GB VRAM
   - 34B: 8GB VRAM

3. **Mixtral**
   - High performance, 12GB VRAM
   - Best for: Complex tasks

## Adding a New Model

1. Download model using Ollama:
   ```bash
   ollama pull your-model-name
   ```

2. Create `models/your-model.yaml`:
   ```yaml
   name: your-model-name
   parameters:
     temperature: 0.7
     max_tokens: 500
     top_p: 1.0
   context_window: 4096
   ```

3. Add to `config.json` models section

## Configuration Format

```yaml
name: model_name
parameters:
  temperature: 0.7
  max_tokens: 500
  top_p: 1.0
context_window: 4096
```

For detailed configuration options, see [Platform Setup Guide](../docs/platform_setup.md#performance-optimization). 