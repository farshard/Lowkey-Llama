"""Test script for Ollama server."""

import sys
import time
import logging
import requests
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from src.ollama_server import OllamaServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_server_connection(max_retries=5, retry_delay=2):
    """Test connection to Ollama server."""
    for i in range(max_retries):
        try:
            # Test version endpoint
            response = requests.get("http://localhost:11434/api/version")
            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"Ollama server is running (version: {version_info.get('version', 'unknown')})")
                return True
                
            logger.warning(f"Unexpected response: {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                logger.info(f"Server not responding, retrying in {retry_delay} seconds... ({i + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to Ollama server")
                return False
                
    return False

def main():
    """Run the test."""
    logger.info("Starting Ollama server test")
    
    # Create and start server
    server = OllamaServer()
    
    try:
        # Start the server
        if not server.start():
            logger.error("Failed to start Ollama server")
            return False
            
        # Test connection
        if not test_server_connection():
            logger.error("Server connection test failed")
            return False
            
        logger.info("Ollama server test completed successfully")
        return True
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return False
        
    finally:
        server.stop()
        
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 