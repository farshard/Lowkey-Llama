import requests
import json

def test_ollama():
    """Test Ollama API with a simple prompt"""
    url = "http://localhost:11434/api/generate"
    
    # Test prompt
    data = {
        "model": "mistral",
        "prompt": "Write a hello world program in Python"
    }
    
    try:
        # Make request
        response = requests.post(url, json=data, stream=True)
        
        # Print response in real-time
        print("\nModel response:")
        print("--------------")
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                print(json_response.get('response', ''), end='')
        print("\n--------------")
        
        print("\nTest successful! Ollama is working correctly.")
        
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama. Make sure it's running.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Ollama connection...")
    test_ollama()