"""Streamlit UI for Local LLM Chat Interface."""

import streamlit as st
import requests
from requests.exceptions import ConnectionError
import json
from gtts import gTTS
import base64
import os
import time
from tempfile import NamedTemporaryFile
import uuid
import atexit
from pathlib import Path
import logging
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API configuration from environment
api_host = os.getenv('API_HOST', 'localhost')
api_port = int(os.getenv('API_PORT', '8001'))  # Default to 8001 if not set
api_base_url = f"http://{api_host}:{api_port}"

logger.info(f"Initializing UI with API endpoint: {api_base_url}")

# Configure page
st.set_page_config(
    page_title="Local LLM Chat Interface",
    page_icon="🤖",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
        .stTextInput > div > div > input {
            background-color: #f0f2f6;
        }
        .stTextArea > div > div > textarea {
            background-color: #f0f2f6;
        }
        .stSelectbox > div > div > select {
            background-color: #f0f2f6;
        }
        .stSlider > div > div > div > div {
            background-color: #f0f2f6;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "models" not in st.session_state:
    st.session_state.models = []

def check_api_health():
    """Check if the API server is healthy."""
    try:
        response = requests.get(f"{api_base_url}/health")
        if response.status_code == 200:
            logger.info("API server is healthy")
            return True
        logger.error(f"API server returned status code: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to API server: {e}")
        return False

def check_ollama_health():
    """Check if Ollama service is healthy."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            logger.info("Ollama service is healthy")
            return True
        logger.error(f"Ollama service returned status code: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to Ollama service: {e}")
        return False

# Check services health
api_healthy = check_api_health()
ollama_healthy = check_ollama_health()

if not api_healthy:
    st.error("⚠️ API server is not responding. Please check if the server is running.")
    st.stop()

if not ollama_healthy:
    st.error("⚠️ Ollama service is not responding. Please check if Ollama is running.")
    st.stop()

# Title
st.title("Local LLM Chat Interface 🤖")

# Clean up function for temporary files
def cleanup_temp_files():
    """Clean up temporary audio files."""
    if hasattr(st.session_state, 'temp_audio_files'):
        for file_path in st.session_state.temp_audio_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to remove temp file {file_path}: {e}")

# Register cleanup function
atexit.register(cleanup_temp_files)

def text_to_speech(text: str) -> str:
    """Convert text to speech and return the audio HTML."""
    try:
        tts = gTTS(text=text, lang='en')
        with NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            if not hasattr(st.session_state, 'temp_audio_files'):
                st.session_state.temp_audio_files = []
            st.session_state.temp_audio_files.append(fp.name)
            
            # Read the audio file and encode it
            with open(fp.name, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
                
            # Create audio HTML
            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    Your browser does not support the audio element.
                </audio>
            """
            return audio_html
    except Exception as e:
        logger.error(f"Text-to-speech failed: {e}")
        return ""

def main():
    """Main UI function."""
    st.title("Local LLM Chat Interface")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tts_enabled" not in st.session_state:
        st.session_state.tts_enabled = False
    if "temp_audio_files" not in st.session_state:
        st.session_state.temp_audio_files = []

    # System Status
    api_status = check_api_health()
    ollama_status = check_ollama_health()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("API Server", "Online ✓" if api_status else "Offline ✗")
    with col2:
        st.metric("Ollama", "Online ✓" if ollama_status else "Offline ✗")
    
    if not api_status or not ollama_status:
        st.error("Some services are offline. Please restart the application.")
        return

    # Model settings section
    st.header("Model Settings")
    available_models = list(config_manager.config.models.keys())
    default_model = config_manager.config.default_model
    default_index = available_models.index(default_model) if default_model in available_models else 0
    
    selected_model = st.selectbox(
        "Choose a model",
        available_models,
        index=default_index
    )
    
    model_config = config_manager.config.models.get(selected_model, {})
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=model_config.temp,
        step=0.1
    )
    
    max_tokens = st.slider(
        "Max Tokens",
        min_value=100,
        max_value=model_config.context_window,
        value=model_config.max_tokens,
        step=100
    )
    
    st.info(f"""Model: {selected_model}
    Context Window: {model_config.context_window}
    Recommended for: {'Code generation' if 'codellama' in selected_model 
                     else 'General reasoning' if 'mixtral' in selected_model
                     else 'Complex tasks' if 'llama2' in selected_model
                     else 'General purpose'}""")

    # TTS settings
    st.header("Text-to-Speech")
    st.session_state.tts_enabled = st.toggle("Enable voice responses", value=st.session_state.tts_enabled)

    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.success("Chat history cleared!")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    prompt = st.chat_input("What's on your mind?")
    
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        try:
            # Get LLM response
            with st.spinner("Generating response..."):
                response = requests.post(
                    f'{api_base_url}/generate',
                    json={
                        "model": selected_model,
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    },
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                response.raise_for_status()
                
                # Process and display assistant response
                result = response.json()
                assistant_response = result.get('response', '')
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                    
                    # Generate and play audio if enabled
                    if st.session_state.tts_enabled:
                        audio_html = text_to_speech(assistant_response)
                        if audio_html:
                            st.components.v1.html(audio_html, height=0)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Chat error: {e}")

if __name__ == "__main__":
    main()
