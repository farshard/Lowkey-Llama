import streamlit as st
import requests
from requests.exceptions import ConnectionError
import json

st.title("Local LLM Chat Interface")

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

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for model selection and parameters
with st.sidebar:
    st.header("Model Settings")
    selected_model = st.selectbox(
        "Choose a model",
        list(MODEL_CONFIGS.keys()),
        index=0
    )
    
    # Get default values for the selected model
    model_config = MODEL_CONFIGS[selected_model]
    
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=model_config["temp"],
        step=0.1,
        help="Higher values make output more creative, lower values more deterministic"
    )
    
    max_tokens = st.slider(
        "Max Tokens",
        min_value=100,
        max_value=model_config["context_window"],
        value=model_config["max_tokens"],
        step=100,
        help="Maximum number of tokens to generate"
    )
    
    st.info(f"""Model: {selected_model}
    Context Window: {model_config['context_window']}
    Recommended for: {'Code generation' if 'codellama' in selected_model 
                     else 'General reasoning' if 'mixtral' in selected_model
                     else 'Complex tasks' if 'llama2' in selected_model
                     else 'General purpose'}""")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What's on your mind?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    try:
        # Prepare request payload
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Get LLM response
        with st.spinner("Generating response..."):
            response = requests.post(
                'http://localhost:11434/api/generate',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            # Process and display assistant response
            result = response.json()
            assistant_response = result.get('response', '')
            
            if assistant_response:
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
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
