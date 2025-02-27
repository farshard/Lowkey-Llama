"""Test Ollama client directly."""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main test function."""
    try:
        # Import OllamaClient from our fixed module
        from src.core.ollama import OllamaClient
        
        # Create client
        client = OllamaClient()
        
        # Test health check
        try:
            healthy = await client.health_check()
            logger.info(f"Ollama health check: {'Healthy' if healthy else 'Unhealthy'}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
        # List models
        try:
            models = await client.list_models()
            logger.info(f"Available models: {models}")
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            
        # Test mistral model with chat
        try:
            logger.info("Testing mistral model with chat...")
            response = await client.chat(
                model="mistral",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, tell me about dogs in one sentence."}
                ],
                options={
                    "temperature": 0.7,
                    "num_predict": 100,
                    "top_p": 0.95,
                    "top_k": 60,
                    "repeat_penalty": 1.18
                }
            )
            logger.info(f"Response: {json.dumps(response, indent=2)}")
        except Exception as e:
            logger.error(f"Chat test failed: {e}", exc_info=True)
            
        # Test mistral-fixed model with chat
        try:
            logger.info("Testing mistral-fixed model with chat...")
            response = await client.chat(
                model="mistral-fixed",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, tell me about dogs in one sentence."}
                ],
                options={
                    "temperature": 0.7,
                    "num_predict": 100,
                    "top_p": 0.95,
                    "top_k": 60,
                    "repeat_penalty": 1.18
                }
            )
            logger.info(f"Response: {json.dumps(response, indent=2)}")
        except Exception as e:
            logger.error(f"Chat test failed: {e}", exc_info=True)
            
        # Close client
        await client.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 