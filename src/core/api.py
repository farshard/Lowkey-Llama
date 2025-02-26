"""FastAPI server for Local LLM Chat Interface."""

import logging
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import uvicorn

from .ollama import OllamaClient, OllamaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
class APIServer:
    """FastAPI server for Local LLM Chat Interface."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize API server.
        
        Args:
            host: Server hostname
            port: Server port
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="Local LLM Chat Interface")
        self.ollama = OllamaClient()
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
        
    def _register_routes(self):
        """Register API routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return HTMLResponse(content="""
                <html>
                    <head>
                        <title>Local LLM Chat Interface API</title>
                    </head>
                    <body>
                        <h1>Local LLM Chat Interface API</h1>
                        <p>Available endpoints:</p>
                        <ul>
                            <li><a href="/health">/health</a> - Health check endpoint</li>
                            <li><a href="/models">/models</a> - List available models</li>
                            <li>/chat - Chat with a model (POST)</li>
                            <li>/chat/stream - WebSocket endpoint for streaming chat</li>
                            <li>/embeddings - Get embeddings for text (POST)</li>
                        </ul>
                    </body>
                </html>
            """)
            
        @self.app.get("/favicon.ico")
        async def favicon():
            """Favicon endpoint."""
            return Response(status_code=204)  # No content response for favicon
            
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Check Ollama service health
                ollama_healthy = await self.ollama.health_check()
                
                # Build health status response
                status = {
                    "status": "healthy" if ollama_healthy else "degraded",
                    "timestamp": time.time(),
                    "components": {
                        "api_server": "healthy",
                        "ollama": "healthy" if ollama_healthy else "unhealthy"
                    }
                }
                
                if not ollama_healthy:
                    logger.warning("Health check: Ollama service is unhealthy")
                    return status
                    
                return status
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail=str(e))
                
        @self.app.get("/models")
        async def list_models() -> List[str]:
            """List available models."""
            try:
                return await self.ollama.list_models()
            except OllamaError as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/chat")
        async def chat(request: ChatRequest) -> Dict:
            """Chat with a model."""
            try:
                logger.info(f"Received chat request for model: {request.model}")
                
                # Use the provided system prompt or the default one
                system_prompt = request.system if request.system else DEFAULT_SYSTEM_PROMPT
                
                # Format the chat context using Mistral's expected format
                formatted_prompt = f"[INST] {system_prompt}\n\n{request.prompt} [/INST]"
                
                # Filter out unsupported parameters
                generate_kwargs = {
                    "model": request.model,
                    "prompt": formatted_prompt,
                }
                
                # Handle options separately
                options = {
                    # Add GPU-specific options to help with CUDA issues
                    "num_gpu": 1,  # Use single GPU
                    "num_thread": 4,  # Reduce thread count
                }
                
                # Add optional parameters if they are provided
                if request.max_tokens:
                    logger.debug(f"Setting max_tokens: {request.max_tokens}")
                    options["num_predict"] = request.max_tokens
                if request.temperature is not None:
                    logger.debug(f"Setting temperature: {request.temperature}")
                    options["temperature"] = request.temperature
                
                # Always include options since we have GPU settings
                generate_kwargs["options"] = options
                
                logger.debug(f"Sending generate request with kwargs: {generate_kwargs}")
                response = await self.ollama.generate(**generate_kwargs)
                
                if not response:
                    logger.error("Ollama returned empty response")
                    raise HTTPException(status_code=500, detail="Failed to generate response")
                
                # Extract the response text from Ollama's response
                response_text = response.get('response', '')
                if not response_text:
                    logger.error(f"Unexpected response format from Ollama: {response}")
                    raise HTTPException(status_code=500, detail="Invalid response format from model")
                
                logger.info("Successfully generated response")
                return {"response": response_text}
                
            except OllamaError as e:
                logger.error(f"Ollama error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.websocket("/chat/stream")
        async def chat_stream(websocket: WebSocket):
            """Streaming chat endpoint."""
            await websocket.accept()
            
            try:
                while True:
                    # Receive request
                    data = await websocket.receive_json()
                    request = ChatRequest(**data)
                    
                    try:
                        # Filter out unsupported parameters
                        generate_kwargs = {
                            "model": request.model,
                            "prompt": request.prompt,
                            "options": {}
                        }
                        
                        # Add optional parameters if they are provided
                        if request.system:
                            generate_kwargs["system"] = request.system
                        if request.template:
                            generate_kwargs["template"] = request.template
                        if request.context:
                            generate_kwargs["context"] = request.context
                        if request.max_tokens:
                            generate_kwargs["options"]["num_predict"] = request.max_tokens
                        
                        # Remove empty options if not used
                        if not generate_kwargs["options"]:
                            del generate_kwargs["options"]
                        
                        # Stream responses
                        async for response in self.ollama.generate(**generate_kwargs):
                            await websocket.send_json(response)
                            
                    except OllamaError as e:
                        await websocket.send_json({"error": str(e)})
                        
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await websocket.send_json({"error": str(e)})
                except:
                    pass
                    
        @self.app.post("/embeddings")
        async def get_embeddings(request: ChatRequest) -> Dict:
            """Get embeddings for text."""
            try:
                return await self.ollama.embeddings(
                    model=request.model,
                    prompt=request.prompt
                )
            except OllamaError as e:
                raise HTTPException(status_code=500, detail=str(e))
                    
    async def start(self):
        """Start the API server."""
        logger.info(f"Starting API server on {self.host}:{self.port}")
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"Failed to start API server: {e}", exc_info=True)
            raise
        
    async def stop(self):
        """Stop the API server."""
        logger.info("Stopping API server")
        await self.ollama.close()

if __name__ == "__main__":
    import asyncio
    
    async def main():
        server = APIServer(host="localhost", port=8001)
        try:
            await server.start()
        except KeyboardInterrupt:
            logger.info("Shutting down API server")
            await server.stop()
        except Exception as e:
            logger.error(f"API server error: {e}", exc_info=True)
            raise
    
    # Run the server
    asyncio.run(main()) 