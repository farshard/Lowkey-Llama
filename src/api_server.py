from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json
import logging
import asyncio
import uvicorn
from typing import Optional, Dict, Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/generate")
async def generate_text(request: GenerationRequest):
    """
    Generate text from a prompt using specified LLM model
    """
    try:
        # Prepare the request payload for Ollama
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "system": "You are a helpful AI assistant.",
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }
        
        logger.debug(f"Sending request to Ollama with payload: {payload}")
        
        # Check if Ollama is running first
        try:
            health_check = requests.get('http://localhost:11434/api/tags', timeout=5)
            health_check.raise_for_status()
        except requests.exceptions.RequestException:
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not running. Please ensure Ollama is installed and running with 'ollama serve'"
            )
        
        # Make the request to Ollama with increased timeout
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=payload,
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=60  # Increased timeout for model loading
        )
        response.raise_for_status()
        
        # Process the streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'error' in chunk:
                        raise HTTPException(status_code=500, detail=chunk['error'])
                    if 'response' in chunk:
                        full_response += chunk['response']
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    continue
        
        if not full_response:
            raise HTTPException(status_code=500, detail="No response generated from the model")
            
        return {"response": full_response}
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        raise HTTPException(
            status_code=504,
            detail="Request timed out. This can happen if the model is still loading or if Ollama is busy."
        )
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama service. Please ensure Ollama is running with 'ollama serve'"
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
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
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "localhost")  # Default to localhost for security
    uvicorn.run(app, host=host, port=port) 