import requests
import pytest

BASE_URL = "http://localhost:8000"

def test_generate_endpoint():
    response = requests.post(
        f"{BASE_URL}/api/generate",
        json={
            "model": "mistral",
            "prompt": "Explain quantum computing in 50 words",
            "max_tokens": 100
        }
    )
    assert response.status_code == 200
    assert "quantum" in response.json()['response'].lower()

def test_list_models():
    response = requests.get(f"{BASE_URL}/api/models")
    assert response.status_code == 200
    assert "mistral" in response.json()['models'] 