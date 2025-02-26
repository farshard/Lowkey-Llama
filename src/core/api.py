"""FastAPI server for Local LLM Chat Interface."""

import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .ollama import OllamaClient, OllamaError

logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    """Chat request model."""
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    stream: bool = False
    raw: bool = False
    format: Optional[str] = None
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
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                is_healthy = await self.ollama.health_check()
                if not is_healthy:
                    raise HTTPException(status_code=503, detail="Ollama service unhealthy")
                return {"status": "healthy"}
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
                response = await self.ollama.generate(
                    model=request.model,
                    prompt=request.prompt,
                    system=request.system,
                    template=request.template,
                    context=request.context,
                    stream=request.stream,
                    raw=request.raw,
                    format=request.format,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                return response
            except OllamaError as e:
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
                        # Stream responses
                        async for response in self.ollama.generate(
                            model=request.model,
                            prompt=request.prompt,
                            system=request.system,
                            template=request.template,
                            context=request.context,
                            stream=True,
                            raw=request.raw,
                            format=request.format,
                            temperature=request.temperature,
                            max_tokens=request.max_tokens
                        ):
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
        import uvicorn
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    async def stop(self):
        """Stop the API server."""
        await self.ollama.close() 