# Local LLM API Documentation

## Overview

The Local LLM API provides a RESTful interface for interacting with local language models through Ollama. The API is built with FastAPI and provides endpoints for text generation, model management, and system health checks. It includes specialized models for factual responses and format compliance.

## Base URL

```
http://localhost:8002
```

## Authentication

The API is designed for local use and currently does not require authentication.

## Endpoints

### Health Check

```http
GET /health
```

Returns the current health status of the API server.

**Response**
```json
{
    "status": "healthy"
}
```

### Generate Text

```http
POST /api/generate
```

Generate text using a specified language model.

**Request Body**
```json
{
    "model": "mistral",
    "prompt": "What is artificial intelligence?",
    "max_tokens": 500,
    "temperature": 0.7
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| model | string | The name of the model to use (e.g., "mistral", "mistral-factual", "mistral-format") |
| prompt | string | The input text to generate from |
| max_tokens | integer | Maximum number of tokens to generate |
| temperature | float | Controls randomness (0.0 to 1.0) |

**Response**
```json
{
    "response": "Artificial intelligence (AI) is a branch of computer science..."
}
```

### List Models

```http
GET /api/models
```

Returns a list of available models.

**Response**
```json
{
    "models": [
        "mistral",
        "codellama:34b-instruct-q4",
        "mixtral:8x7b-instruct-q4"
    ]
}
```

## Specialized Models

### mistral-format

Specialized for strict format compliance and word count requirements:

```http
POST /api/generate
```

**Request Body**
```json
{
    "model": "mistral-format",
    "prompt": "Define AI in exactly three words",
    "temperature": 0.01
}
```

This model:
- Uses extremely low temperature (0.01) for consistent formatting
- Has strict format enforcement with zero tolerance
- Returns "Format error" if unable to match format exactly
- Excludes ALL explanations, prefixes, suffixes, or punctuation
- Optimized parameters:
  - Temperature: 0.01 (almost deterministic)
  - Top-p: 0.1 (extremely focused sampling)
  - Top-k: 3 (minimal token selection)

**Example Request/Response**
```
Request: "what is a fact in three words?"
❌ "Fact: Truth verified" (has prefix)
❌ "Information true" (only two words)
❌ "Information requires verification." (has punctuation)
✓ "Format error" (when format cannot be matched exactly)
```

### mistral-factual

Optimized for format-first factual responses with zero tolerance for format errors:

```http
POST /api/generate
```

**Request Body**
```json
{
    "model": "mistral-factual",
    "prompt": "what is a fact in three words?",
    "temperature": 0.01
}
```

This model:
- Uses extremely low temperature (0.01) for deterministic outputs
- Has zero tolerance for format violations
- Returns "Format error" if format requirements cannot be met exactly
- Optimized parameters:
  - Temperature: 0.01 (almost completely deterministic)
  - Top-p: 0.1 (extremely focused sampling)
  - Top-k: 3 (minimal token selection)

**Example Request/Response**
```
Request: "what is a fact in three words?"
❌ "A verified truth" (needs verification)
❌ "Information requires verification" (format error - punctuation)
✓ "Format error" (when format cannot be matched exactly)
```

Both models are designed with a strict "format-first" approach, meaning they will return "Format error" rather than provide an incorrect or improperly formatted response. This behavior ensures reliability and predictability in applications requiring exact format compliance.

## Error Handling

The API uses standard HTTP status codes and returns error messages in JSON format:

```json
{
    "detail": "Error message describing what went wrong"
}
```

Common status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error
- 503: Service Unavailable (Ollama not running)

## Rate Limiting

The API currently does not implement rate limiting as it's designed for local use.

## Examples

### Testing for Hallucinations

The API provides endpoints to test and validate model responses for factual accuracy:

```http
POST /chat
```

**Request Body**
```json
{
    "model": "mistral-factual",
    "prompt": "What is dark matter made of at the quantum level?",
    "temperature": 0.5
}
```

Example test cases for evaluating factual accuracy:

```python
import requests

def test_model_accuracy(prompt: str, model: str = "mistral-factual") -> str:
    response = requests.post(
        "http://localhost:8002/chat",
        json={
            "model": model,
            "prompt": prompt,
            "temperature": 0.5
        }
    )
    response.raise_for_status()
    return response.json()["response"]

# Test cases
test_cases = [
    "What will be the dominant programming language in 2030?",  # Future prediction
    "What is dark matter made of at the quantum level?",       # Scientific uncertainty
    "What were the major AI breakthroughs in 2023?",          # Recent events
    "How does consciousness emerge in the brain?"              # Complex topic
]

for prompt in test_cases:
    print(f"\nTesting: {prompt}")
    response = test_model_accuracy(prompt)
    print(f"Response: {response}")
```

### Python

```python
import requests

def generate_text(prompt: str, model: str = "mistral") -> str:
    response = requests.post(
        "http://localhost:8002/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "max_tokens": 500,
            "temperature": 0.7
        }
    )
    response.raise_for_status()
    return response.json()["response"]

# Example usage
result = generate_text("Explain quantum computing")
print(result)
```

### JavaScript

```javascript
async function generateText(prompt, model = "mistral") {
    const response = await fetch("http://localhost:8002/api/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            model,
            prompt,
            max_tokens: 500,
            temperature: 0.7
        })
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.response;
}

// Example usage
generateText("Explain quantum computing")
    .then(response => console.log(response))
    .catch(error => console.error(error));
```

### Format-Specific Queries

```python
import requests

def get_formatted_response(prompt: str, word_count: int = 3) -> str:
    response = requests.post(
        "http://localhost:8002/api/generate",
        json={
            "model": "mistral-format",
            "prompt": f"{prompt} in exactly {word_count} words",
            "temperature": 0.1
        }
    )
    response.raise_for_status()
    return response.json()["response"]

# Example usage
result = get_formatted_response("Define artificial intelligence")
print(result)  # Example output: "Machines Learning Intelligence"
```

## Best Practices

1. **Error Handling**: Always implement proper error handling in your applications.
2. **Connection Management**: Check the API health before making requests.
3. **Resource Management**: Be mindful of model loading times and memory usage.
4. **Prompt Engineering**: Structure your prompts clearly for better results.

## Limitations

1. The API is designed for local use only and should not be exposed to the internet.
2. Response times may vary based on:
   - Model size
   - Available system resources
   - Whether the model is already loaded
3. Memory usage depends on the model size and number of concurrent requests.

## Support

For issues and feature requests, please visit our GitHub repository:
[https://github.com/farshard/Lowkey-Llama](https://github.com/farshard/Lowkey-Llama) 