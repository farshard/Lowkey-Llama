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
from typing import List, Dict
import logging

from src.core.config import ConfigManager
from src.core.services import ServiceManager

# Initialize config manager
config_manager = ConfigManager()
service_manager = ServiceManager(config_manager)

# Initialize logger
logger = logging.getLogger(__name__)

def check_api_health():
    """Check if the API server is running and responsive"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            return health_data.get('status') == 'healthy'
        return False
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"API health check failed: {e}")
        return False

def check_ollama_health():
    """Check if Ollama is running and responsive"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

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
    
    # Ollama Settings
    st.header("Advanced Settings")
    with st.expander("Ollama Configuration"):
        current_path = config_manager.config.paths.ollama or ""
        
        # Display current Ollama status
        if service_manager.is_ollama_process_running():
            st.success("✓ Ollama is running")
            if current_path:
                st.info(f"Current Ollama path: {current_path}")
        else:
            st.error("✕ Ollama is not running")
            if current_path:
                st.warning(f"Configured path: {current_path} (not running)")
            else:
                st.warning("No Ollama path configured")
        
        new_path = st.text_input(
            "Ollama Path", 
            value=current_path,
            help="Full path to ollama.exe (e.g., C:\\Program Files\\Ollama\\ollama.exe)"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("Update Ollama Path"):
                if new_path != current_path:
                    if new_path:  # If a path was provided
                        is_valid, error = service_manager.validate_ollama_executable(new_path)
                        if is_valid:
                            try:
                                config_manager.save_user_config({
                                    "paths": {"ollama": new_path}
                                })
                                st.success("✓ Ollama path updated! Please restart the application for changes to take effect.")
                            except Exception as e:
                                st.error(f"Failed to save configuration: {str(e)}")
                        else:
                            st.error(f"Invalid Ollama executable: {error}")
                    else:  # If path was cleared
                        try:
                            config_manager.save_user_config({
                                "paths": {"ollama": None}
                            })
                            st.success("✓ Reset to default path")
                        except Exception as e:
                            st.error(f"Failed to reset configuration: {str(e)}")
        with col2:
            if st.button("Reset to Default"):
                try:
                    config_manager.save_user_config({
                        "paths": {"ollama": None}
                    })
                    st.success("✓ Reset to default path")
                    new_path = ""
                except Exception as e:
                    st.error(f"Failed to reset configuration: {str(e)}")
        with col3:
            if st.button("Detect Path"):
                detected_path = service_manager.find_ollama_path()
                if detected_path:
                    st.success(f"✓ Found Ollama at: {detected_path}")
                    new_path = detected_path
                else:
                    st.error("Could not detect Ollama path automatically")
                    st.info("Please install Ollama from https://ollama.ai/download")

    # Installation Help (moved outside the Ollama Configuration expander)
    with st.expander("Installation Help"):
        st.markdown("""
        ### Installing Ollama
        
        1. Download Ollama from [ollama.ai/download](https://ollama.ai/download)
        2. Run the installer
        3. Restart your computer if needed
        4. Click 'Detect Path' above to automatically find Ollama
        
        Common installation paths:
        - Windows: `C:\\Program Files\\Ollama\\ollama.exe`
        - macOS: `/opt/homebrew/bin/ollama` or `/usr/local/bin/ollama`
        - Linux: `/usr/local/bin/ollama`
        
        If Ollama is not found automatically:
        1. Open a terminal/command prompt
        2. Run `ollama --version`
        3. If it works, Ollama is in your PATH
        4. If not, find the full path to ollama.exe and enter it above
        """)

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
                    'http://localhost:8000/generate',
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
                
                if assistant_response:
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)
                        # Generate and play audio if TTS is enabled
                        if st.session_state.tts_enabled:
                            audio_html = text_to_speech(assistant_response)
                            if audio_html:
                                st.markdown(audio_html, unsafe_allow_html=True)
                else:
                    st.error("Received empty response from the model")
                
        except ConnectionError:
            error_message = "⚠️ Cannot connect to Ollama. Please make sure it's running on localhost:11434"
            st.error(error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"⚠️ API request failed: {str(e)}"
            st.error(error_message)
        except json.JSONDecodeError as e:
            error_message = f"⚠️ Invalid JSON response: {str(e)}"
            st.error(error_message)
        except Exception as e:
            error_message = f"⚠️ An error occurred: {str(e)}"
            st.error(error_message)

def text_to_speech(text):
    """Convert text to speech and return the audio player HTML"""
    try:
        # Create a unique filename using UUID
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"audio_{uuid.uuid4()}.mp3")
        
        # Clean up old temporary files
        for old_file in st.session_state.temp_audio_files:
            try:
                if os.path.exists(old_file):
                    os.unlink(old_file)
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Generate speech
        tts = gTTS(text=text, lang='en')
        # Save to file
        tts.save(temp_file)
        
        # Add new file to cleanup list
        st.session_state.temp_audio_files.append(temp_file)
        
        # Read the file
        with open(temp_file, 'rb') as audio_file:
            audio_bytes = audio_file.read()
        
        # Encode to base64
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Create audio HTML with controls
        audio_html = f'''
            <audio autoplay controls>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Your browser does not support the audio element.
            </audio>
        '''
        return audio_html
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        return None

# Cleanup function for temp files
def cleanup_temp_files():
    for file in st.session_state.temp_audio_files:
        try:
            if os.path.exists(file):
                os.unlink(file)
        except Exception:
            pass
    st.session_state.temp_audio_files = []

# Register cleanup function
atexit.register(cleanup_temp_files)

if __name__ == "__main__":
    main()
