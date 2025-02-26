"""FastAPI server for Local LLM Chat Interface."""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager
import logging
from fastapi.responses import JSONResponse

from src.core.ollama import OllamaClient, OllamaError
from src.core.config import ConfigManager

logger = logging.getLogger(__name__)
config_manager = ConfigManager()
ollama_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage API lifespan."""
    global ollama_client
    try:
        # Initialize Ollama client
        ollama_client = OllamaClient()
        
        # Try to connect with retries
        max_retries = 5
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                if await ollama_client.health_check():
                    logger.info("Successfully connected to Ollama service")
                    break
                raise OllamaError("Ollama service is not healthy")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to connect to Ollama (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to Ollama after {max_retries} attempts")
                    raise
                    
        yield
    except Exception as e:
        logger.error(f"Error during API server startup: {e}")
        raise
    finally:
        if ollama_client:
            await ollama_client.close()

app = FastAPI(lifespan=lifespan)

# Constants for validation
MAX_TOKENS_LIMIT = 4096  # Maximum tokens allowed for generation
MODEL_CONTEXT_WINDOWS = {
    "mistral": 8192,
    "codellama": 16384,
    "llama2": 4096
}

async def get_ollama_client() -> OllamaClient:
    """Get Ollama client instance."""
    if not ollama_client:
        raise HTTPException(
            status_code=503,
            detail="API server is starting up or Ollama client is not initialized"
        )
    return ollama_client

@app.get("/health")
async def health_check(client: OllamaClient = Depends(get_ollama_client)):
    """Health check endpoint."""
    try:
        if await client.health_check(timeout=1.0):
            return {"status": "healthy"}
        return JSONResponse(
            status_code=503,
            content={"detail": "Ollama service is not healthy"}
        )
    except OllamaError as e:
        return JSONResponse(
            status_code=503,
            content={"detail": str(e)}
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"detail": str(e)}
        )

@app.get("/models")
async def list_models(client: OllamaClient = Depends(get_ollama_client)):
    """List available models."""
    try:
        models = await client.list_models()
        return {"models": [model["name"] for model in models]}
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The prompt to generate from")
    model: str = Field(..., min_length=1, description="The model to use for generation")
    max_tokens: int = Field(
        default=500,
        gt=0,
        le=4096,
        description="Maximum tokens to generate (1 to 4096)"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for generation (0.0 to 1.0)"
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model name."""
        if not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

@app.post("/generate")
async def generate(request: GenerateRequest, client: OllamaClient = Depends(get_ollama_client)):
    """Generate text from model."""
    try:
        logger.info(f"Received generate request for model {request.model}")
        
        # Validate model exists
        try:
            models = await client.list_models()
            logger.info(f"Available models: {[m['name'] for m in models]}")
            if not any(m["name"] == request.model for m in models):
                logger.error(f"Model {request.model} not found in available models")
                raise HTTPException(
                    status_code=404,
                    detail=f"Model {request.model} not found"
                )
        except OllamaError as e:
            logger.error(f"Failed to list models: {e}")
            raise HTTPException(status_code=503, detail=str(e))

        # Set up generation options
        options = {
            "temperature": request.temperature,
            "num_predict": request.max_tokens
        }
        logger.info(f"Generation options: {options}")

        # Format prompt according to model template
        formatted_prompt = f"[INST] {request.prompt} [/INST]"
        logger.info(f"Formatted prompt: {formatted_prompt}")

        # Generate response
        response_text = []
        try:
            logger.info("Starting generation...")
            async for chunk in client.generate(
                model=request.model,
                prompt=formatted_prompt,
                options=options
            ):
                if "response" in chunk:
                    response_text.append(chunk["response"])
                    logger.debug(f"Received chunk: {chunk['response']}")
                elif "error" in chunk:
                    logger.error(f"Error in generation chunk: {chunk['error']}")
                    raise OllamaError(chunk["error"])
                
            if not response_text:
                logger.error("No response generated")
                raise OllamaError("No response generated")
                
            response = {"response": "".join(response_text)}
            logger.info("Generation completed successfully")
            return response
            
        except asyncio.TimeoutError:
            logger.error("Generation timed out")
            raise HTTPException(status_code=504, detail="Generation timed out")
        except OllamaError as e:
            logger.error(f"Generation failed: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to generate response: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 