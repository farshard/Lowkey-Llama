import os
import json
import socket
import psutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
import streamlit as st

class PrivacyManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.privacy_mode: bool = False
        self.conversation_history_enabled: bool = True
        self.allowed_ip_ranges: List[str] = ["127.0.0.1"]
        self.load_config()
        
    def load_config(self) -> None:
        """Load privacy settings from config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                privacy_config = config.get('privacy', {})
                self.privacy_mode = privacy_config.get('privacy_mode', False)
                self.conversation_history_enabled = privacy_config.get('enable_conversation_history', True)
                self.allowed_ip_ranges = privacy_config.get('allowed_ip_ranges', ["127.0.0.1"])
        except FileNotFoundError:
            logging.warning(f"Config file {self.config_path} not found. Using default privacy settings.")
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in config file {self.config_path}")

    def save_config(self) -> None:
        """Save privacy settings to config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            config['privacy'] = {
                'privacy_mode': self.privacy_mode,
                'enable_conversation_history': self.conversation_history_enabled,
                'allowed_ip_ranges': self.allowed_ip_ranges
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save privacy settings: {str(e)}")

    def configure_environment(self) -> None:
        """Configure environment variables for privacy."""
        os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        os.environ["STREAMLIT_SERVER_ADDRESS"] = "localhost"
        os.environ["OLLAMA_HOST"] = "localhost"
        os.environ["OLLAMA_NO_TELEMETRY"] = "true"

    def verify_telemetry_disabled(self) -> Dict[str, bool]:
        """Verify that telemetry is disabled for all components."""
        status = {
            "streamlit_telemetry": os.getenv("STREAMLIT_BROWSER_GATHER_USAGE_STATS") == "false",
            "ollama_telemetry": os.getenv("OLLAMA_NO_TELEMETRY") == "true",
            "localhost_only": all(host == "localhost" for host in [
                os.getenv("STREAMLIT_SERVER_ADDRESS"),
                os.getenv("OLLAMA_HOST")
            ])
        }
        return status

    def clear_conversation_history(self) -> None:
        """Clear all conversation history."""
        if "messages" in st.session_state:
            st.session_state.messages = []
        
        # Clear cache directory
        cache_dir = Path("cache")
        if cache_dir.exists():
            for file in cache_dir.glob("*"):
                try:
                    file.unlink()
                except Exception as e:
                    logging.error(f"Failed to delete cache file {file}: {str(e)}")

    def verify_network_isolation(self) -> Dict[str, bool]:
        """Verify network isolation status."""
        def is_local_address(addr: str) -> bool:
            return addr in ["localhost", "127.0.0.1"] or addr.startswith("192.168.") or addr.startswith("10.")

        status = {
            "streamlit_local": is_local_address(os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")),
            "ollama_local": is_local_address(os.getenv("OLLAMA_HOST", "localhost")),
            "api_local": True  # Assuming API is always local
        }
        return status

    def get_active_connections(self) -> Set[str]:
        """Get list of active network connections for the application."""
        connections = set()
        try:
            for conn in psutil.net_connections():
                if conn.status == 'ESTABLISHED':
                    connections.add(f"{conn.laddr.ip}:{conn.laddr.port} -> {conn.raddr.ip}:{conn.raddr.port}")
        except Exception as e:
            logging.error(f"Failed to get network connections: {str(e)}")
        return connections

    def audit_dependencies(self) -> Dict[str, Dict[str, bool]]:
        """Audit dependencies for potential privacy concerns."""
        dependencies = {
            "streamlit": {
                "has_telemetry": True,
                "can_disable": True,
                "is_disabled": os.getenv("STREAMLIT_BROWSER_GATHER_USAGE_STATS") == "false"
            },
            "ollama": {
                "has_telemetry": True,
                "can_disable": True,
                "is_disabled": os.getenv("OLLAMA_NO_TELEMETRY") == "true"
            },
            "requests": {
                "has_telemetry": False,
                "can_disable": False,
                "is_disabled": True
            }
        }
        return dependencies

    def toggle_privacy_mode(self, enable: bool) -> None:
        """Toggle privacy mode on/off."""
        self.privacy_mode = enable
        if enable:
            self.configure_environment()
        self.save_config()

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if an IP address is allowed to access the application."""
        return ip in self.allowed_ip_ranges or ip == "127.0.0.1" or ip == "localhost" 