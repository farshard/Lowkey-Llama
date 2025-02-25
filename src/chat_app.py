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
from privacy import PrivacyManager

# Initialize privacy manager
privacy_manager = PrivacyManager()
privacy_manager.configure_environment()

st.title("Local LLM Chat Interface")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tts_enabled" not in st.session_state:
    st.session_state.tts_enabled = False
if "temp_audio_files" not in st.session_state:
    st.session_state.temp_audio_files = []
if "privacy_mode" not in st.session_state:
    st.session_state.privacy_mode = privacy_manager.privacy_mode

# Model configurations
MODEL_CONFIGS = {
    "mistral": {
        "temp": 0.7,
        "max_tokens": 500,
        "context_window": 4096
    },
    "codellama:34b-instruct-q4": {
        "temp": 0.5,
        "max_tokens": 2048,
        "context_window": 8192
    },
    "mixtral:8x7b-instruct-q4": {
        "temp": 0.7,
        "max_tokens": 4096,
        "context_window": 16384
    },
    "llama2:70b-q4": {
        "temp": 0.8,
        "max_tokens": 4096,
        "context_window": 4096
    }
}

# Sidebar for settings
with st.sidebar:
    st.header("Privacy Settings")
    privacy_mode = st.toggle(
        "Privacy Mode",
        value=st.session_state.privacy_mode,
        help="Enable enhanced privacy features"
    )
    
    # Update privacy mode if changed
    if privacy_mode != st.session_state.privacy_mode:
        privacy_manager.toggle_privacy_mode(privacy_mode)
        st.session_state.privacy_mode = privacy_mode
    
    # Show privacy status
    if privacy_mode:
        st.success("🔒 Privacy Mode Active")
        telemetry_status = privacy_manager.verify_telemetry_disabled()
        network_status = privacy_manager.verify_network_isolation()
        
        with st.expander("Privacy Status"):
            for key, value in telemetry_status.items():
                st.write(f"{'✅' if value else '❌'} {key.replace('_', ' ').title()}")
            for key, value in network_status.items():
                st.write(f"{'✅' if value else '❌'} {key.replace('_', ' ').title()}")
    
    # Conversation history settings
    st.header("History Settings")
    enable_history = st.checkbox(
        "Enable Conversation History",
        value=privacy_manager.conversation_history_enabled,
        help="Store chat history locally"
    )
    if enable_history != privacy_manager.conversation_history_enabled:
        privacy_manager.conversation_history_enabled = enable_history
        privacy_manager.save_config()
    
    if st.button("Clear All Data"):
        privacy_manager.clear_conversation_history()
        st.success("All conversation history and cache cleared!")

    # Model settings section
    st.header("Model Settings")
    selected_model = st.selectbox(
        "Choose a model",
        list(MODEL_CONFIGS.keys()),
        index=0
    )
    
    model_config = MODEL_CONFIGS[selected_model]
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=model_config["temp"],
        step=0.1
    )
    
    max_tokens = st.slider(
        "Max Tokens",
        min_value=100,
        max_value=model_config["context_window"],
        value=model_config["max_tokens"],
        step=100
    )
    
    st.info(f"""Model: {selected_model}
    Context Window: {model_config['context_window']}
    Recommended for: {'Code generation' if 'codellama' in selected_model 
                     else 'General reasoning' if 'mixtral' in selected_model
                     else 'Complex tasks' if 'llama2' in selected_model
                     else 'General purpose'}""")

    # TTS settings
    st.header("Text-to-Speech")
    st.session_state.tts_enabled = st.toggle("Enable voice responses", value=st.session_state.tts_enabled)

# Display privacy warning if needed
if not all(privacy_manager.verify_network_isolation().values()):
    st.warning("⚠️ Warning: Application may be accessible from external networks. Enable Privacy Mode for enhanced security.")

# Display chat messages
if privacy_manager.conversation_history_enabled:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What's on your mind?"):
    # Add user message to chat history
    if privacy_manager.conversation_history_enabled:
        st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    try:
        # Get LLM response
        with st.spinner("Generating response..."):
            response = requests.post(
                'http://localhost:8000/api/generate',
                json={
                    "model": selected_model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                headers={'Content-Type': 'application/json'},
                timeout=30  # Add 30-second timeout
            )
            response.raise_for_status()
            
            # Process and display assistant response
            result = response.json()
            assistant_response = result.get('response', '')
            
            if assistant_response:
                if privacy_manager.conversation_history_enabled:
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                    # Generate and play audio if TTS is enabled
                    if st.session_state.tts_enabled and not privacy_mode:  # Disable TTS in privacy mode
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

# Add dependency audit information
with st.sidebar:
    st.header("Security Audit")
    with st.expander("Dependency Audit"):
        dependencies = privacy_manager.audit_dependencies()
        for dep, info in dependencies.items():
            st.write(f"**{dep}**")
            for key, value in info.items():
                st.write(f"- {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}")

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
