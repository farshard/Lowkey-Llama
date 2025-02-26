"""Ollama API client for Local LLM Chat Interface."""

import json
import logging
import asyncio
from typing import Dict, List, Optional, AsyncGenerator, Union
import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass

class OllamaClient:
    """Client for interacting with the Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the client.
        
        Args:
            base_url: Base URL for Ollama API
        """
        self.base_url = base_url
        self._session = None
        
    async def __aenter__(self):
        """Enter async context."""
        await self.ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self.close()
        
    async def ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def health_check(self) -> bool:
        """Check if Ollama server is healthy.
        
        Returns:
            bool: True if server is healthy
        """
        try:
            await self.ensure_session()
            async with self._session.get(f"{self.base_url}/api/version") as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
            
    async def list_models(self) -> List[str]:
        """List available models.
        
        Returns:
            List[str]: List of model names
        """
        try:
            await self.ensure_session()
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and "models" in data:
                        # New API format
                        return [model["name"] for model in data["models"]]
                    elif isinstance(data, list):
                        # Old API format
                        return [model["name"] for model in data]
                    else:
                        # Simplest format - just return the model names directly
                        return [str(model) for model in data] if isinstance(data, list) else []
                return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
            
    async def pull_model(self, name: str) -> AsyncGenerator[Dict, None]:
        """Pull a model from Ollama.
        
        Args:
            name: Name of the model to pull
            
        Yields:
            Dict: Progress information
        """
        try:
            await self.ensure_session()
            async with self._session.post(
                f"{self.base_url}/api/pull",
                json={"name": name},
                timeout=None
            ) as response:
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "error" in data:
                                raise Exception(data["error"])
                            yield {
                                "status": data.get("status", ""),
                                "completed": data.get("completed", 0),
                                "total": data.get("total", 0)
                            }
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            raise
            
    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        template: str = "",
        context: List[int] = None,
        options: Dict = None,
        max_tokens: int = None
    ) -> Optional[Dict]:
        """Generate a response from the model.
        
        Args:
            model: Name of the model to use
            prompt: Input prompt
            system: System prompt
            template: Custom prompt template
            context: Token context from previous responses
            options: Model-specific options
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict: Model response
        """
        try:
            await self.ensure_session()
            
            request = {
                "model": model,
                "prompt": prompt
            }
            
            if system:
                request["system"] = system
            if template:
                request["template"] = template
            if context:
                request["context"] = context
            if max_tokens is not None:
                if not options:
                    options = {}
                options["num_predict"] = max_tokens
            if options:
                request["options"] = options
                
            logger.debug(f"Sending request to Ollama: {request}")
            
            async with self._session.post(
                f"{self.base_url}/api/generate",
                json=request,
                timeout=ClientTimeout(total=120)  # Increase timeout for long generations
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {error_text}")
                    raise OllamaError(f"Ollama API returned status {response.status}: {error_text}")
                
                # Read the first line of the response
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "error" in data:
                                raise OllamaError(data["error"])
                            return data
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode Ollama response: {e}")
                            continue
                
                logger.error("No valid response received from Ollama")
                return None
                
        except asyncio.TimeoutError:
            logger.error("Request to Ollama timed out")
            raise OllamaError("Request timed out")
        except Exception as e:
            logger.error(f"Failed to generate response: {e}", exc_info=True)
            raise OllamaError(f"Failed to generate response: {str(e)}")
            
    async def embeddings(self, model: str, prompt: str) -> Dict:
        """Get embeddings for text.
        
        Args:
            model: Name of the model to use
            prompt: Text to get embeddings for
            
        Returns:
            Dict containing the embeddings
        """
        try:
            await self.ensure_session()
            async with self._session.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": prompt}
            ) as response:
                if response.status != 200:
                    raise OllamaError(f"Failed to get embeddings: {response.status}")
                    
                data = await response.json()
                if "error" in data:
                    raise OllamaError(data["error"])
                return data
                
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            raise OllamaError(f"Failed to get embeddings: {e}") 