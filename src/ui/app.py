"""Streamlit UI for Lowkey Llama."""

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

# Import ConfigManager using absolute import from src
from src.core.config import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration
config_manager = ConfigManager(config_path=str(project_root / "config.json"))

# Get API configuration from environment
api_host = os.getenv('API_HOST', 'localhost')
api_port = int(os.getenv('API_PORT', '8001'))  # Changed from 8000 to 8001
api_base_url = f"http://{api_host}:{api_port}"

logger.info(f"Initializing UI with API endpoint: {api_base_url}")

# Configure page
st.set_page_config(
    page_title="Lowkey Llama",
    page_icon="🦙",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved UI
st.markdown("""
<style>
.stMarkdown h1 {
    font-size: 2.5rem !important;
}
.stChatMessage {
    font-size: 1.1rem;
    line-height: 1.6;
}
.stTextInput input, .stTextArea textarea {
    font-size: 1.1rem !important;
}
.stButton button {
    font-size: 1.1rem !important;
    padding: 0.5rem 1.5rem !important;
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
st.title("Lowkey Llama")

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
    # Logo with constrained dimensions
    logo_col = st.columns([1])[0]
    with logo_col:
        st.image("assets/lowkey-logo.png", width=300)  # Ideal width for most screens
        
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

    # Add the custom model if it exists but isn't in config
    try:
        all_models = requests.get(f"{api_base_url}/models").json()
        for model in all_models:
            if model not in available_models and model.startswith("mistral"):
                available_models.append(model)
    except Exception as e:
        logger.error(f"Failed to get additional models: {e}")

    default_model = config_manager.config.default_model
    if "mistral-fixed" in available_models:
        default_model = "mistral-fixed"  # Prefer our fixed model
    
    default_index = available_models.index(default_model) if default_model in available_models else 0

    selected_model = st.selectbox(
        "Choose a model",
        available_models,
        index=default_index
    )

    # Add note about fixed models
    if "mistral" in selected_model:
        if "fixed" in selected_model:
            st.success("✅ You're using the optimized Mistral model with improved response completeness.")
        else:
            st.warning("⚠️ The standard Mistral model may give truncated responses. Try 'mistral-fixed' for better results.")

    # Get model configuration (with fallback for new models)
    try:
        model_config = config_manager.get_model_config(selected_model)
    except ValueError:
        # Model not in config yet, use default values
        logger.info(f"Model {selected_model} not found in config, using defaults")
        from src.core.config import ModelConfig
        model_config = ModelConfig()
        
        # Add this model to configuration 
        config_manager.add_model_config(selected_model, model_config.model_dump())
    
    # Update info box for mistral-fixed specifically
    if selected_model == "mistral-fixed":
        st.info(f"""Model: {selected_model}
        Context Window: {model_config.context_window}
        Recommended for: General reasoning with comprehensive responses
        Optimizations: Enhanced prompting and parameters for detailed outputs""")
    else:
        st.info(f"""Model: {selected_model}
        Context Window: {model_config.context_window}
        Recommended for: {'Code generation' if 'codellama' in selected_model 
                         else 'General reasoning' if 'mixtral' in selected_model
                         else 'Complex tasks' if 'llama2' in selected_model
                         else 'General purpose'}""")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=getattr(model_config, 'temp', 0.8),
        step=0.1
    )
    
    # Now set up slider with fallback values if needed
    max_tokens = st.slider(
        "Max tokens to generate",
        min_value=10,
        max_value=getattr(model_config, 'context_window', 4096) if hasattr(model_config, 'context_window') else 4096,
        value=min(getattr(model_config, 'max_tokens', 2048), 2048),  # Use default or cap at 2048
        step=10
    )
    
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
                # Construct a better request with all necessary parameters
                request_data = {
                    "model": selected_model,
                    "prompt": f"{prompt}\n\nPlease give a detailed and complete answer:",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    # Use a more forceful system prompt
                    "system": "You are a helpful assistant. You MUST ALWAYS provide detailed, complete answers with multiple sentences. NEVER give short or one-word responses. Your answers should be comprehensive and thorough."
                }
                
                response = requests.post(
                    f'{api_base_url}/chat',
                    json=request_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=120  # Increase timeout for longer responses
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
