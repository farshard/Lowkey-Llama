# API Documentation

The Local LLM Chat Interface provides a RESTful API for integrating local language models into your applications.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing authentication using FastAPI's security features.

## Endpoints

### Generate Text

Generate text responses from the LLM model.

```http
POST /api/generate
```

#### Request Body

```json
{
  "model": "mistral",
  "prompt": "string",
  "max_tokens": 500,
  "temperature": 0.7
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| model | string | The name of the Ollama model to use (default: "mistral") |
| prompt | string | The input text prompt |
| max_tokens | integer | Maximum number of tokens to generate (default: 500) |
| temperature | float | Sampling temperature (0.0 to 1.0, default: 0.7) |

#### Response

```json
{
  "response": "string"
}
```

#### Example

```bash
curl -X POST "http://localhost:8000/api/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "mistral",
           "prompt": "What is machine learning?",
           "max_tokens": 100,
           "temperature": 0.7
         }'
```

### List Models

Get a list of available Ollama models.

```http
GET /api/models
```

#### Response

```json
{
  "models": [
    "mistral",
    "llama2",
    "codellama"
  ]
}
```

#### Example

```bash
curl "http://localhost:8000/api/models"
```

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a detail message:

```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

Currently, there is no rate limiting implemented. For production use, consider adding rate limiting using FastAPI middleware.

## Streaming Responses

Streaming responses are not yet implemented but planned for future releases. This will allow for real-time text generation.

## Best Practices

1. **Error Handling**
   - Always handle potential API errors in your client code
   - Implement retry logic for transient failures

2. **Resource Management**
   - Keep prompts concise and focused
   - Monitor token usage to optimize costs

3. **Performance**
   - Cache frequently used responses
   - Use appropriate max_tokens values

## SDK Examples

### Python

```python
import requests

def generate_text(prompt, model="mistral"):
    response = requests.post(
        "http://localhost:8000/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "max_tokens": 500,
            "temperature": 0.7
        }
    )
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
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            model,
            prompt,
            max_tokens: 500,
            temperature: 0.7
        }),
    });
    const data = await response.json();
    return data.response;
}

// Example usage
generateText("Explain quantum computing")
    .then(result => console.log(result))
    .catch(error => console.error(error));
``` 