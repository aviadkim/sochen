#!/usr/bin/env python3
"""
Sochen - AI agent system for collaborative software development.
Main entry point for the application.
"""
import asyncio
import argparse
import logging
import sys
import os

from agent_system.config import Config
from agent_system.state import AgentState
from agent_system.memory.vector_store import VectorStore
from agent_system.graph import DependencyGraph
from agent_system.server import SochenServer

def setup_logging(config: Config) -> None:
    """Set up logging configuration."""
    log_level = config.get('logging.level', 'INFO')
    log_file = config.get('logging.file', 'sochen.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Sochen - AI agent system for collaborative software development')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--server', action='store_true', help='Start the HTTP server')
    args = parser.parse_args()
    
    # Initialize config
    config = Config(args.config)
    
    # Set up logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Sochen")
    
    # Initialize state
    state = AgentState()
    
    # Initialize memory
    memory_path = config.get('memory.storage_path', '.memory')
    memory = VectorStore(memory_path)
    
    # Initialize dependency graph
    graph = DependencyGraph()
    
    # Set default project name from directory name if not set
    if not state.get('project_name'):
        current_dir = os.path.basename(os.getcwd())
        state.set('project_name', current_dir)
    
    if args.server:
        # Start the HTTP server
        server = SochenServer(config, state, memory)
        await server.start()
    else:
        # Print help if no arguments provided
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
