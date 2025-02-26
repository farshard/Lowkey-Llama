# Local LLM API Documentation

## Overview

The Local LLM API provides a RESTful interface for interacting with local language models through Ollama. The API is built with FastAPI and provides endpoints for text generation, model management, and system health checks.

## Base URL

```
http://localhost:8000
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
| model | string | The name of the model to use |
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

### Python

```python
import requests

def generate_text(prompt: str, model: str = "mistral") -> str:
    response = requests.post(
        "http://localhost:8000/api/generate",
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
    const response = await fetch("http://localhost:8000/api/generate", {
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
[https://github.com/voolyvex/Local-LLM](https://github.com/voolyvex/Local-LLM) 