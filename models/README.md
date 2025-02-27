# Model Configurations 🧠

Configuration files for language models supported by the Local LLM Chat Interface.

## Available Models

1. **Mistral (Default)**
   - General purpose, 4GB VRAM
   - Best for: Chat, writing, analysis

2. **Mistral-Fixed (Recommended)**
   - Optimized for detailed, complete responses
   - Fixes truncation issues in standard Mistral
   - Same resource requirements as Mistral

3. **CodeLlama**
   - Code generation specialist
   - 13B: 5GB VRAM
   - 34B: 8GB VRAM

4. **Mixtral**
   - High performance, 12GB VRAM
   - Best for: Complex tasks

## Creating a Custom Model

1. Download a base model using Ollama:
   ```bash
   ollama pull mistral
   ```

2. Create a modelfile (see `mistral-fixed.modelfile` for example):
   ```
   FROM base-model
   
   PARAMETER temperature 0.7
   PARAMETER top_p 0.95
   PARAMETER top_k 60
   PARAMETER num_ctx 8192
   
   SYSTEM """Your system prompt here..."""
   ```

3. Build the custom model:
   ```bash
   ollama create my-custom-model -f models/my-custom-model.modelfile
   ```

4. Add to `config.json` models section (optional):
   ```json
   "models": {
     "my-custom-model": {
       "temp": 0.7,
       "max_tokens": 4096, 
       "context_window": 8192
     }
   }
   ```

## Optimizing Your Models

Different use cases require different parameter settings:

- **General chat**: temperature 0.7-0.8, top_p 0.9
- **Code generation**: temperature 0.5-0.6, top_p 0.95
- **Creative writing**: temperature 0.8-0.9, top_p 0.95, top_k 60
- **Detailed responses**: repeat_penalty 1.15-1.2, top_p 0.9-0.95

For comprehensive optimization guide, see [custom_models.md](../docs/custom_models.md).

## Configuration Format

```yaml
name: model_name
parameters:
  temperature: 0.7
  max_tokens: 500
  top_p: 1.0
context_window: 4096
```

## Example: Mistral-Fixed Model

This model solves the truncated response issues with Mistral:

```
FROM mistral

# Parameter optimization for detailed responses
PARAMETER temperature 0.7
PARAMETER top_p 0.95
PARAMETER top_k 60
PARAMETER num_ctx 8192
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.18
PARAMETER repeat_last_n 64
PARAMETER seed 42

# More detailed system prompt
SYSTEM """You are a helpful assistant specialized in providing comprehensive answers.
...
"""
```

See the full modelfile for details. 