"""
Configuration for the agent system.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent_system.log")
    ]
)
logger = logging.getLogger("agent_system")

# API keys and configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY is required. Set it in your .env file or environment variables.")

# WebSocket server configuration
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))

# Model configuration
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.1

# Initialize LLM
def get_llm(model=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE):
    """Get a configured Gemini LLM instance."""
    try:
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True,
            safety_settings=[
                {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise

# Project paths
def get_project_root():
    """Get the project root directory."""
    # For now, assume the current working directory is the project root
    return os.getcwd()

class Config:
    """Configuration manager for the Sochen system."""
    
    DEFAULT_CONFIG = {
        "api_keys": {
            "openai": ""
        },
        "server": {
            "host": "127.0.0.1",
            "port": 3000
        },
        "logging": {
            "level": "INFO",
            "file": "sochen.log"
        },
        "memory": {
            "storage_path": ".memory"
        },
        "agents": {
            "architect": {
                "model": "gpt-4",
                "temperature": 0.2
            },
            "coder": {
                "model": "gpt-4",
                "temperature": 0.1
            },
            "reviewer": {
                "model": "gpt-4",
                "temperature": 0.0
            }
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        if config_path is None:
            # Use default location
            home_dir = str(Path.home())
            config_path = os.path.join(home_dir, ".sochen", "config.json")
        
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load config if it exists
        if os.path.exists(config_path):
            self.load_config()
        else:
            # Create default config
            self.save_config()
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                loaded_config = json.load(f)
                # Update our config with loaded values, preserving defaults for missing keys
                self._update_nested_dict(self.config, loaded_config)
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key (can use dot notation for nested keys)
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key (can use dot notation for nested keys)
            value: The value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the right level
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save the updated config
        self.save_config()
    
    def _update_nested_dict(self, d: Dict[str, Any], u: Dict[str, Any]) -> None:
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            d: The dictionary to update
            u: The dictionary with update values
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
