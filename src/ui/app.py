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
api_port = int(os.getenv('API_PORT', '8002'))  # Using port 8002
api_base_url = f"http://{api_host}:{api_port}"

# Only log initialization once at startup
if "initialized" not in st.session_state:
    logger.info(f"Initializing UI with API endpoint: {api_base_url}")
    st.session_state.initialized = True
    st.session_state.last_health_check = 0
    st.session_state.health_check_interval = 30  # Check health every 30 seconds
    st.session_state.theme_mode = "dark"  # Default to dark mode

# Set theme before page config
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

# Configure page with theme
st.set_page_config(
    page_title="Lowkey Llama",
    page_icon="🦙",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Lowkey Llama - Your Local AI Assistant"
    }
)

# Custom CSS for improved UI with dark mode support
st.markdown("""
<style>
/* Base styles */
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
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

/* Hover effects */
.stButton button:hover {
    filter: brightness(110%) !important;
    transform: translateY(-1px) !important;
}

/* Select box improvements */
.stSelectbox select {
    cursor: pointer !important;
}

.stSelectbox [data-baseweb="select"] {
    cursor: pointer !important;
}

.stSelectbox [data-baseweb="select"] * {
    cursor: pointer !important;
}

.stSelectbox:hover {
    filter: brightness(105%) !important;
}

/* Slider improvements */
.stSlider input {
    cursor: pointer !important;
}

/* Chat input improvements */
.stChatInputContainer {
    cursor: text !important;
}

/* Toggle/checkbox improvements */
.stCheckbox input {
    cursor: pointer !important;
}

.stCheckbox:hover {
    filter: brightness(105%) !important;
}

/* Dark mode styles */
[data-theme="dark"] {
    background-color: #0E1117 !important;
    color: #FAFAFA !important;
}

[data-theme="dark"] .stMarkdown {
    color: #FAFAFA !important;
}

[data-theme="dark"] .stTextInput input,
[data-theme="dark"] .stTextArea textarea {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A4A !important;
}

[data-theme="dark"] .stButton button {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A4A !important;
}

[data-theme="dark"] .stSelectbox select {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}

/* Force dark mode */
.main {
    background-color: var(--background-color);
    color: var(--text-color);
}

/* Additional dark mode elements */
[data-theme="dark"] .stAlert,
[data-theme="dark"] .stInfo {
    background-color: #1E1E1E !important;
    color: #FAFAFA !important;
}

[data-theme="dark"] .stMetric {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}

[data-theme="dark"] .stChatMessage {
    background-color: #262730 !important;
    border-color: #4A4A4A !important;
}
</style>
""", unsafe_allow_html=True)

# Force dark mode using JavaScript
st.markdown("""
<script>
    // Force dark mode
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.setAttribute('data-theme', 'dark');
    
    // Monitor system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.body.setAttribute('data-theme', 'dark');
    });
</script>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "models" not in st.session_state:
    st.session_state.models = []

def check_api_health(silent=True):
    """Check API health with rate limiting."""
    current_time = time.time()
    if current_time - st.session_state.last_health_check < st.session_state.health_check_interval:
        return True  # Skip check if too soon
        
    try:
        response = requests.get(f"{api_base_url}/health", timeout=2)
        is_healthy = response.status_code == 200
        if not silent:
            if is_healthy:
                logger.info("API server is healthy")
            else:
                logger.error("API server is not healthy")
        st.session_state.last_health_check = current_time
        return is_healthy
    except Exception as e:
        if not silent:
            logger.error(f"API health check failed: {e}")
        st.session_state.last_health_check = current_time
        return False

def check_ollama_health(silent=True):
    """Check Ollama health with rate limiting."""
    current_time = time.time()
    if current_time - st.session_state.last_health_check < st.session_state.health_check_interval:
        return True  # Skip check if too soon
        
    try:
        response = requests.get(f"{api_base_url}/health")
        if response.status_code == 200:
            if not silent:
                logger.info("Ollama service is healthy")
            st.session_state.last_health_check = current_time
            return True
    except Exception as e:
        if not silent:
            logger.error(f"Ollama health check failed: {e}")
    st.session_state.last_health_check = current_time
    return False

# Check services health silently (with rate limiting)
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

def ensure_model_config_updated(config_manager, model_name: str) -> None:
    """Ensure model configuration is up to date with latest settings."""
    try:
        if "mistral" in model_name.lower():
            if "factual" in model_name.lower():
                updates = {
                    "temp": 0.01,  # Almost completely deterministic
                    "top_p": 0.1,  # Extremely focused sampling
                    "top_k": 3,    # Minimal token selection
                    "system_prompt": """You are a format-first factual assistant with ZERO TOLERANCE for format errors.

ABSOLUTE RULES - NO EXCEPTIONS:
1. ONLY output the exact number of words requested - nothing more, nothing less
2. NO prefixes, suffixes, punctuation, or explanations
3. NO "Fact:", "Note:", parentheses, or any other additions
4. NO apologies or corrections
5. If format isn't perfect, output ONLY "Format error"

Word counting process:
1. Write response
2. Count words (hyphenated=1, numbers=1, contractions=1)
3. If not EXACT count, delete and write "Format error"
4. If exact count, remove ALL punctuation
5. Final verification - count again
6. Send ONLY the words or "Format error"

Example request: "what is a fact in three words"
❌ "Fact: Truth verified" (has prefix)
❌ "Information true" (only two words)
❌ "Information requires verification." (has punctuation)
❌ "(Information requires verification)" (has parentheses)
✓ "Information requires verification" (exactly three words)

Remember: ONLY output the exact words or "Format error". Nothing else."""
                }
            elif "format" in model_name.lower():
                updates = {
                    "temp": 0.01,  # Almost completely deterministic
                    "top_p": 0.1,  # Extremely focused sampling
                    "top_k": 3,    # Minimal token selection
                    "system_prompt": """You are a format-first assistant with ZERO TOLERANCE for format errors.

ABSOLUTE RULES - NO EXCEPTIONS:
1. ONLY output the exact number of words requested - nothing more, nothing less
2. NO prefixes, suffixes, punctuation, or explanations
3. NO parentheses or any other additions
4. NO apologies or corrections
5. If format isn't perfect, output ONLY "Format error"

Word counting process:
1. Write response
2. Count words (hyphenated=1, numbers=1, contractions=1)
3. If not EXACT count, delete and write "Format error"
4. If exact count, remove ALL punctuation
5. Final verification - count again
6. Send ONLY the words or "Format error"

Example request: "what is a fact in three words"
❌ "A fact: Information true" (4 words)
❌ "Information true" (only two words)
❌ "Information requires verification." (has punctuation)
❌ "(Information requires verification)" (has parentheses)
✓ "Information requires verification" (exactly three words)

Remember: ONLY output the exact words or "Format error". Nothing else."""
                }
            else:
                return  # No updates needed for base model
                
            try:
                config_manager.update_model_config(model_name, updates)
                logger.info(f"Updated configuration for {model_name}")
            except ValueError:
                # Model doesn't exist yet, add it
                config_manager.add_model_config(model_name, updates)
                logger.info(f"Added new configuration for {model_name}")
    except Exception as e:
        logger.error(f"Failed to update model configuration: {e}")

def main():
    """Main UI function."""
    # Logo with constrained dimensions
    logo_col = st.columns([1])[0]
    with logo_col:
        st.image("assets/lowkey-logo-blu-300.png", width=300)

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

    # Initialize available_models and selected_model
    available_models = []
    default_model = config_manager.config.default_model
    selected_model = default_model

    try:
        # Get available models from API
        response = requests.get(f"{api_base_url}/models")
        if response.status_code == 200:
            available_models = response.json()
            # Filter out :latest tags and get base names
            available_models = [model.split(':')[0] if ':' in model else model for model in available_models]
            # Sort models alphabetically
            available_models.sort()
            
            # If default model isn't in available models, use the first one
            if default_model not in available_models and available_models:
                selected_model = available_models[0]
        else:
            st.error("Failed to fetch available models from API")
            available_models = list(config_manager.config.models.keys())  # Fallback to config models
    except Exception as e:
        st.error(f"Error fetching models: {str(e)}")
        available_models = list(config_manager.config.models.keys())  # Fallback to config models

    # Model selection
    selected_model = st.selectbox(
        "Select Model",
        options=available_models,
        index=available_models.index(selected_model) if selected_model in available_models else 0,
        help="Choose the model to use for chat. Each model is optimized for different tasks."
    )

    # Get model configuration (with fallback for new models)
    try:
        model_config = config_manager.get_model_config(selected_model)
        # Ensure configuration is up to date
        ensure_model_config_updated(config_manager, selected_model)
    except ValueError:
        # Model not in config yet, use default values
        logger.info(f"Model {selected_model} not found in config, creating new configuration")
        from src.core.config import ModelConfig
        model_config = ModelConfig()
        
        # Add model-specific configurations
        if "mistral" in selected_model.lower():
            if "factual" in selected_model.lower():
                config_dict = {
                    "temp": 0.01,  # Almost completely deterministic
                    "top_p": 0.1,  # Extremely focused sampling
                    "top_k": 3,    # Minimal token selection
                    "system_prompt": """You are a format-first factual assistant with ZERO TOLERANCE for format errors.

ABSOLUTE RULES - NO EXCEPTIONS:
1. ONLY output the exact number of words requested - nothing more, nothing less
2. NO prefixes, suffixes, punctuation, or explanations
3. NO "Fact:", "Note:", parentheses, or any other additions
4. NO apologies or corrections
5. If format isn't perfect, output ONLY "Format error"

Word counting process:
1. Write response
2. Count words (hyphenated=1, numbers=1, contractions=1)
3. If not EXACT count, delete and write "Format error"
4. If exact count, remove ALL punctuation
5. Final verification - count again
6. Send ONLY the words or "Format error"

Example request: "what is a fact in three words"
❌ "Fact: Truth verified" (has prefix)
❌ "Information true" (only two words)
❌ "Information requires verification." (has punctuation)
❌ "(Information requires verification)" (has parentheses)
✓ "Information requires verification" (exactly three words)

Remember: ONLY output the exact words or "Format error". Nothing else."""
                }
            elif "format" in selected_model.lower():
                config_dict = {
                    "temp": 0.01,  # Almost completely deterministic
                    "top_p": 0.1,  # Extremely focused sampling
                    "top_k": 3,    # Minimal token selection
                    "system_prompt": """You are a format-first assistant with ZERO TOLERANCE for format errors.

ABSOLUTE RULES - NO EXCEPTIONS:
1. ONLY output the exact number of words requested - nothing more, nothing less
2. NO prefixes, suffixes, punctuation, or explanations
3. NO parentheses or any other additions
4. NO apologies or corrections
5. If format isn't perfect, output ONLY "Format error"

Word counting process:
1. Write response
2. Count words (hyphenated=1, numbers=1, contractions=1)
3. If not EXACT count, delete and write "Format error"
4. If exact count, remove ALL punctuation
5. Final verification - count again
6. Send ONLY the words or "Format error"

Example request: "what is a fact in three words"
❌ "A fact: Information true" (4 words)
❌ "Information true" (only two words)
❌ "Information requires verification." (has punctuation)
❌ "(Information requires verification)" (has parentheses)
✓ "Information requires verification" (exactly three words)

Remember: ONLY output the exact words or "Format error". Nothing else."""
                }
            else:
                config_dict = {
                    "temp": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "system_prompt": """You are a helpful, detailed assistant. You always:
                    1. Provide complete, thorough responses
                    2. Follow formatting instructions precisely
                    3. Structure your responses clearly
                    4. Stay focused on the question
                    If given specific formatting requirements, you MUST follow them exactly."""
                }
            
            # Update model config with the new settings
            for key, value in config_dict.items():
                setattr(model_config, key, value)
            
            # Save the configuration
            try:
                config_manager.add_model_config(selected_model, model_config.model_dump())
                logger.info(f"Successfully saved configuration for {selected_model}")
            except Exception as e:
                logger.error(f"Failed to save model configuration: {e}")

    # Add model-specific information
    if "mistral" in selected_model.lower():
        if "factual" in selected_model.lower():
            st.success("✅ Using mistral-factual: Optimized for accuracy and reduced hallucination.")
            st.info(f"""Model: {selected_model}
            Context Window: {model_config.context_window}
            Recommended for: Factual responses with high accuracy
            Optimizations:
            - Temperature: {model_config.temp} (lower for more deterministic outputs)
            - Top-p: {model_config.top_p} (controlled sampling)
            - Top-k: {model_config.top_k} (limited token selection)""")
        elif "format" in selected_model.lower():
            st.success("✅ Using mistral-format: Optimized for precise formatting and structured responses.")
            st.info(f"""Model: {selected_model}
            Context Window: {model_config.context_window}
            Recommended for: Format-specific tasks and structured outputs
            Optimizations:
            - Temperature: {model_config.temp} (balanced for creativity and precision)
            - Top-p: {model_config.top_p} (controlled diversity)
            - Top-k: {model_config.top_k} (balanced token selection)""")
        else:
            st.info(f"""Model: {selected_model}
            Context Window: {model_config.context_window}
            Recommended for: General purpose tasks
            Consider using:
            - mistral-factual for high accuracy
            - mistral-format for precise formatting""")

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
                # Construct request with enhanced parameters
                request_data = {
                    "model": selected_model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": model_config.system_prompt,
                    "top_p": model_config.top_p,
                    "top_k": model_config.top_k,
                    "repeat_penalty": model_config.repeat_penalty,
                    "presence_penalty": model_config.presence_penalty,
                    "frequency_penalty": model_config.frequency_penalty
                }
                
                response = requests.post(
                    f'{api_base_url}/chat',
                    json=request_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=120
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
