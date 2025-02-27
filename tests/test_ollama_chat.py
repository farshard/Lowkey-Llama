"""Test script for debugging Ollama chat API responses."""

import sys
import os
import json
import asyncio
import aiohttp
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path to allow imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class OllamaTestClient:
    """Test client for Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._session = None
        
    async def ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def chat_raw(self, model: str, messages, options=None):
        """Send a raw chat request and return full details about the response."""
        await self.ensure_session()
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        if options:
            payload["options"] = options
            
        logger.info(f"Sending chat request to Ollama: {payload}")
        
        result = {
            "status": None,
            "headers": None,
            "body_text": None,
            "content_type": None,
            "parsed_json": None,
            "error": None
        }
            
        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                result["status"] = response.status
                result["headers"] = dict(response.headers)
                result["content_type"] = response.headers.get("Content-Type", "")
                
                # Get the raw text response
                body_text = await response.text()
                result["body_text"] = body_text
                
                # Try to parse as JSON
                try:
                    if "application/x-ndjson" in result["content_type"]:
                        # Handle ndjson line by line
                        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
                        result["parsed_lines"] = []
                        
                        for i, line in enumerate(lines):
                            try:
                                parsed = json.loads(line)
                                result["parsed_lines"].append({"index": i, "content": parsed})
                            except json.JSONDecodeError as e:
                                result["parsed_lines"].append({"index": i, "error": str(e), "line": line})
                                
                        # If last line is valid JSON, use it as final result
                        if lines and "parsed_lines" in result and result["parsed_lines"]:
                            last_valid = None
                            for line_info in reversed(result["parsed_lines"]):
                                if "content" in line_info:
                                    last_valid = line_info["content"]
                                    break
                            if last_valid:
                                result["parsed_json"] = last_valid
                    else:
                        # Try to parse as regular JSON
                        result["parsed_json"] = json.loads(body_text)
                except Exception as e:
                    result["parse_error"] = str(e)
                    
        except Exception as e:
            result["error"] = str(e)
            
        return result

async def test_chat_api():
    """Test the Ollama chat API."""
    client = OllamaTestClient()
    
    # Define test cases
    test_cases = [
        {
            "name": "Basic chat request",
            "model": "mistral-fixed",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about dogs in three sentences."}
            ],
            "options": {
                "temperature": 0.7,
                "top_p": 0.95
            }
        }
    ]
    
    # Run each test case
    for test_case in test_cases:
        logger.info(f"Running test case: {test_case['name']}")
        
        # Request using raw API to get full details
        response = await client.chat_raw(
            test_case["model"],
            test_case["messages"],
            test_case.get("options", None)
        )
        
        # Print detailed response information
        print(f"\n--- RESPONSE FOR {test_case['name']} ---")
        print(f"Status: {response['status']}")
        print(f"Content-Type: {response['content_type']}")
        print(f"Headers: {json.dumps(response['headers'], indent=2)}")
        
        # Print the response body
        if response.get("body_text"):
            print(f"\nBody length: {len(response['body_text'])} chars")
            print(f"Body preview: {response['body_text'][:500]}...")
            
        # Print parsed JSON if available
        if response.get("parsed_json"):
            print(f"\nParsed JSON: {json.dumps(response['parsed_json'], indent=2)}")
            
        # Print any lines parsed from ndjson
        if response.get("parsed_lines"):
            print(f"\nParsed {len(response['parsed_lines'])} JSON lines:")
            for i, line_info in enumerate(response["parsed_lines"]):
                if i < 3 or i >= len(response["parsed_lines"]) - 3:  # Show first 3 and last 3
                    print(f"  Line {line_info['index']}: {json.dumps(line_info.get('content', line_info))}")
                elif i == 3 and len(response["parsed_lines"]) > 6:
                    print(f"  ... {len(response['parsed_lines']) - 6} more lines ...")
            
        # Print any errors
        if response.get("error"):
            print(f"\nError: {response['error']}")
        if response.get("parse_error"):
            print(f"\nParse error: {response['parse_error']}")
            
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_chat_api()) 