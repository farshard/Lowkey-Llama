"""FastAPI server for Lowkey Llama."""

import logging
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import uvicorn
import multiprocessing
import aiohttp
import asyncio
import sys
import subprocess
import os
from pathlib import Path

from .ollama import OllamaClient, OllamaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app at module level
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
    
@app.get("/models")
async def list_models():
    """List available models."""
    try:
        async with OllamaClient() as client:
            models = await client.list_models()
            return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define a comprehensive system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. Your responses should be:
1. Detailed and informative
2. Clear and well-structured
3. Written in a natural, conversational style
4. Accurate and factual
5. Engaging but professional

If you don't know something, say so honestly. If a question is unclear, ask for clarification."""

class ChatRequest(BaseModel):
    """Chat request model."""
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    stream: bool = False  # Used only for WebSocket endpoint
    raw: bool = False    # Used only for WebSocket endpoint
    format: Optional[str] = None  # Used only for WebSocket endpoint
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ModelInfo(BaseModel):
    """Model information."""
    name: str
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint."""
    try:
        async with OllamaClient() as client:
            # Prepare the messages
            messages = [
                {"role": "system", "content": request.system or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": request.prompt}
            ]
            
            # Prepare options
            options = {
                "temperature": request.temperature or 0.7,
                "num_predict": request.max_tokens or 1000
            }
            
            # Log the request for debugging
            logger.debug(f"Sending chat request: model={request.model}, messages={messages}, options={options}")
            
            # Make the request to Ollama
            response = await client.chat(
                model=request.model,
                messages=messages,
                options=options
            )
            
            # Log the response for debugging
            logger.debug(f"Received response from Ollama: {response}")
            
            # Extract the message content
            if isinstance(response, dict):
                if "message" in response and isinstance(response["message"], dict):
                    return {"response": response["message"].get("content", "")}
                elif "response" in response:
                    return {"response": response["response"]}
            
            # If we get here, something went wrong with the response format
            logger.error(f"Unexpected response format: {response}")
            raise HTTPException(status_code=500, detail="Unexpected response format from model")
            
    except OllamaError as e:
        logger.error(f"Ollama error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
class APIServer:
    """API server for Local LLM."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize API server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.process = None
        self.startup_complete = False
            
    async def start(self):
        """Start the API server."""
        try:
            # First check if we're already running
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{self.host}:{self.port}/health") as response:
                        if response.status == 200:
                            logger.info("API server is already running")
                            self.startup_complete = True
                            return
            except Exception:
                pass  # Expected if server is not running
            
            # Start server in a separate process using subprocess
            cmd = [
                sys.executable,
                "-m", "uvicorn",
                "src.core.api:app",
                "--host", self.host,
                "--port", str(self.port),
                "--log-level", "info",
                "--no-access-log"
            ]
            
            # Set PYTHONPATH to include project root
            env = dict(os.environ)
            env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)
            
            logger.info(f"Starting API server with command: {' '.join(cmd)}")
            logger.info(f"PYTHONPATH: {env['PYTHONPATH']}")
            
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(Path(__file__).parent.parent.parent)  # Set working directory to project root
            )
            
            # Wait for server to be ready
            start_time = time.time()
            timeout = 30
            last_check = 0
            
            while time.time() - start_time < timeout:
                # Check process status
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    logger.error(f"API server process died during startup.")
                    logger.error(f"Stdout: {stdout}")
                    logger.error(f"Stderr: {stderr}")
                    raise Exception(f"API server process died during startup. Stdout: {stdout}, Stderr: {stderr}")
                
                # Only check health every 100ms
                current_time = time.time()
                if current_time - last_check < 0.1:
                    await asyncio.sleep(0.01)
                    continue
                    
                last_check = current_time
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://{self.host}:{self.port}/health") as response:
                            if response.status == 200:
                                self.startup_complete = True
                                logger.info("API server started successfully")
                                return
                except Exception:
                    await asyncio.sleep(0.1)
                    continue
                    
            # If we get here, we timed out
            stdout, stderr = self.process.communicate()
            logger.error(f"API server failed to start within timeout.")
            logger.error(f"Stdout: {stdout}")
            logger.error(f"Stderr: {stderr}")
            raise Exception("API server failed to start within timeout")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            if self.process and self.process.poll() is None:
                self.process.terminate()
            raise
            
    async def stop(self):
        """Stop the API server."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                
    async def health_check(self) -> bool:
        """Check if server is healthy."""
        try:
            if not self.process or self.process.poll() is not None:
                return False
                
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{self.host}:{self.port}/health") as response:
                    return response.status == 200
        except Exception:
            return False

if __name__ == "__main__":
    import asyncio
    
    async def main():
        server = APIServer(host="localhost", port=8001)
        try:
            await server.start()
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down API server")
            await server.stop()
        except Exception as e:
            logger.error(f"API server error: {e}", exc_info=True)
            raise
    
    # Run the server
    asyncio.run(main()) 