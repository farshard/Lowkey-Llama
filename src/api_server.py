from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json

app = FastAPI(title="LLM API Server")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerationRequest(BaseModel):
    model: str = "mistral"
    prompt: str
    max_tokens: int = 500
    temperature: float = 0.7

@app.post("/api/generate")
async def generate_text(request: GenerationRequest):
    """
    Generate text from a prompt using specified LLM model
    """
    try:
        # Prepare the request payload
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }
        
        # Make the request to Ollama
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=payload
        )
        response.raise_for_status()
        
        # Parse and return the response
        result = response.json()
        return {"response": result.get('response', '')}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    """
    List available Ollama models
    """
    try:
        response = requests.get('http://localhost:11434/api/tags')
        response.raise_for_status()
        models = response.json().get('models', [])
        return {"models": [m.get('name', '') for m in models]}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 