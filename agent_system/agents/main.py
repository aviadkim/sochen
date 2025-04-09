"""
Main entry point for the agent system.
"""
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Ensure the agent_system module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Load environment variables from .env file
load_dotenv()

# Import server module
from agent_system.server import start_server
from agent_system.config import logger

if __name__ == "__main__":
    logger.info("Starting Agent System")
    
    try:
        # Check for required environment variables
        if not os.getenv("GEMINI_API_KEY"):
            logger.error("GEMINI_API_KEY environment variable is not set")
            print("Error: GEMINI_API_KEY environment variable is not set")
            print("Please set it in a .env file or in your environment")
            sys.exit(1)
        
        # Start the server
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"Error: {e}")
        sys.exit(1)