import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required tools are installed"""
    requirements = {
        'ollama': 'curl https://ollama.ai/install.sh | sh',
        'python': 'Already installed',
        'git': 'https://git-scm.com/downloads'
    }
    
    missing = []
    
    # Check Ollama
    try:
        subprocess.run(['ollama', '--version'], capture_output=True)
    except FileNotFoundError:
        missing.append('ollama')
    
    # Check Git
    try:
        subprocess.run(['git', '--version'], capture_output=True)
    except FileNotFoundError:
        missing.append('git')
    
    return missing

def setup_environment():
    """Set up Python virtual environment and install dependencies"""
    subprocess.run([sys.executable, '-m', 'venv', 'llm_env'])
    
    # Activate virtual environment
    if os.name == 'nt':  # Windows
        activate_script = Path('llm_env/Scripts/activate')
    else:  # Unix/Linux
        activate_script = Path('llm_env/bin/activate')
    
    # Install required packages
    pip_cmd = [sys.executable, '-m', 'pip', 'install', 
               'streamlit', 'requests', 'python-dotenv']
    subprocess.run(pip_cmd)

def create_chat_interface():
    """Create a simple Streamlit chat interface"""
    with open('chat_app.py', 'w') as f:
        f.write('''
import streamlit as st
import requests

st.title("Local LLM Chat Interface")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

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
    
    # Get LLM response
    response = requests.post('http://localhost:11434/api/generate',
                           json={
                               "model": "mistral",
                               "prompt": prompt
                           })
    
    # Process and display assistant response
    assistant_response = response.json()['response']
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    
    with st.chat_message("assistant"):
        st.markdown(assistant_response)
''')

def main():
    print("Setting up local LLM environment...")
    
    # Check requirements
    missing_reqs = check_requirements()
    if missing_reqs:
        print("Missing required tools:", missing_reqs)
        print("Please install them before continuing.")
        return
    
    # Set up environment
    setup_environment()
    
    # Create chat interface
    create_chat_interface()
    
    print("\nSetup complete! To start chatting:")
    print("1. Run: ollama pull mistral")
    print("2. Run: streamlit run chat_app.py")

if __name__ == "__main__":
    main()