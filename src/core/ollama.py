"""Ollama API client for Lowkey Llama."""

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
            
    async def generate(self, **kwargs):
        """Generate a response from the model."""
        url = f"{self.base_url}/api/generate"
        await self.ensure_session()
        
        # Special handling for Mistral models
        if "mistral" in kwargs.get("model", "").lower():
            # Clear any potentially problematic options
            if "options" not in kwargs:
                kwargs["options"] = {}
            
            # Use chat completion format instead of generate for Mistral
            chat_url = f"{self.base_url}/api/chat"
            
            # Format as a proper chat message
            messages = [
                {
                    "role": "system",
                    "content": kwargs.get("system", "You are a helpful assistant who always gives detailed, multi-sentence responses.")
                },
                {
                    "role": "user", 
                    "content": f"{kwargs.get('prompt', '')} Please provide a detailed response with multiple sentences."
                }
            ]
            
            # Use the chat endpoint instead
            try:
                chat_data = {
                    "model": kwargs.get("model"),
                    "messages": messages,
                    "options": {
                        "temperature": kwargs["options"].get("temperature", 0.7),
                        "num_predict": kwargs["options"].get("num_predict", 4096),
                        "top_p": kwargs["options"].get("top_p", 0.9),
                        "top_k": 40,
                        "repeat_penalty": 1.1
                    }
                }
                
                async with self._session.post(chat_url, json=chat_data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    # Extract response from chat format
                    return {"response": result.get("message", {}).get("content", "")}
            except Exception as e:
                logger.error(f"Chat endpoint failed, falling back to generate: {e}")
                # Continue with generate as fallback
        
        try:
            async with self._session.post(url, json=kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            raise OllamaError(f"Ollama API error: {e.status} {e.message}")
        except Exception as e:
            raise OllamaError(f"Failed to generate: {str(e)}")
            
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
            
    async def chat(self, model: str, messages: List[Dict], options: Optional[Dict] = None) -> Dict:
        """Chat completion API for Ollama.
        
        Args:
            model: Model name
            messages: List of message dictionaries with role and content
            options: Optional parameters for the model
            
        Returns:
            Dict: Response from the API
        """
        try:
            await self.ensure_session()
            
            payload = {
                "model": model,
                "messages": messages
            }
            
            if options:
                payload["options"] = options
                
            logger.debug(f"Sending chat request with payload: {payload}")
            
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Chat API error: {response.status} - {error_text}")
                    raise OllamaError(f"Chat API error: {response.status} - {error_text}")
                    
                content_type = response.headers.get('Content-Type', '')
                logger.debug(f"Response content type: {content_type}")
                
                # Read the entire content
                body_text = await response.text()
                
                # If we got an ndjson response, we need to process all the lines
                if 'application/x-ndjson' in content_type or body_text.count('\n') > 1:
                    # Process ndjson line by line
                    lines = [line.strip() for line in body_text.split('\n') if line.strip()]
                    logger.debug(f"Received {len(lines)} lines of ndjson")
                    
                    # Initialize variables to track state
                    final_message = {"role": "assistant", "content": ""}
                    complete_content = ""
                    
                    for line in lines:
                        try:
                            # Parse the line as JSON
                            data = json.loads(line)
                            
                            # Accumulate token-by-token content
                            if "message" in data and "content" in data["message"]:
                                content_chunk = data["message"]["content"]
                                complete_content += content_chunk
                                
                                # Keep updating our final message with accumulated content
                                final_message["content"] = complete_content
                                
                            # Check if it's the final message with done=true
                            if data.get("done", False):
                                logger.debug("Found final message with done=true")
                                # Return the result with final content
                                return {"message": final_message}
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON line: {e}")
                    
                    # If we've processed all lines but didn't find a done=true marker
                    # Return what we have accumulated
                    if complete_content:
                        logger.debug(f"No done=true marker found, returning accumulated content: {len(complete_content)} chars")
                        return {"message": final_message}
                    else:
                        # Try one more approach - get the last valid line and use it
                        for line in reversed(lines):
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    logger.debug("Using last line as final message")
                                    return data
                            except:
                                continue
                                
                        # If we still can't find a valid response, raise an error
                        logger.error("Failed to extract valid response from ndjson lines")
                        raise OllamaError("Failed to extract valid response from model output")
                        
                # If it's a regular JSON response, just parse it directly
                else:
                    try:
                        # First try parsing as a single JSON object
                        result = json.loads(body_text)
                        logger.debug(f"Parsed JSON response: {result}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.debug(f"Raw response: {body_text[:500]}...")
                        
                        # As a fallback, try to extract any valid JSON from the response
                        try:
                            # Try to find JSON-like content in the response
                            import re
                            json_matches = re.findall(r'\{[^{}]*\}', body_text)
                            if json_matches:
                                for potential_json in json_matches:
                                    try:
                                        result = json.loads(potential_json)
                                        if "message" in result or "content" in result:
                                            logger.debug(f"Found valid JSON in response: {result}")
                                            return result
                                    except:
                                        continue
                        except Exception as extraction_error:
                            logger.error(f"JSON extraction fallback failed: {extraction_error}")
                        
                        # If we still can't parse it, construct a simple response
                        if body_text.strip():
                            logger.warning(f"Returning raw text as content due to JSON parse failure")
                            return {"message": {"role": "assistant", "content": body_text.strip()}}
                        
                        raise OllamaError(f"Failed to parse Ollama response: {e}")
                        
        except aiohttp.ClientResponseError as e:
            logger.error(f"Client response error: {e}")
            raise OllamaError(f"Chat API error: {e.status} {e.message}")
        except Exception as e:
            logger.error(f"Failed to complete chat: {str(e)}", exc_info=True)
            raise OllamaError(f"Failed to complete chat: {str(e)}") 