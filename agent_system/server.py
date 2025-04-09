"""
HTTP server for the Sochen API.
"""
import asyncio
import logging
import json
from typing import Dict, Any, Optional
from aiohttp import web

from .state import AgentState
from .config import Config
from .agents import ArchitectAgent, CoderAgent, ReviewerAgent
from .memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

class SochenServer:
    """
    HTTP server for the Sochen API.
    Provides endpoints for interacting with agents and accessing system state.
    """
    
    def __init__(self, config: Config, state: AgentState, memory: VectorStore):
        """
        Initialize the server.
        
        Args:
            config: System configuration
            state: Agent state
            memory: Vector store for agent memory
        """
        self.config = config
        self.state = state
        self.memory = memory
        self.app = web.Application()
        self.setup_routes()
        
        # Initialize agents
        self.architect = ArchitectAgent(state, memory)
        self.coder = CoderAgent(state, memory)
        self.reviewer = ReviewerAgent(state, memory)
        
        logger.info("Sochen server initialized")
    
    def setup_routes(self) -> None:
        """Set up the API routes."""
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/status', self.handle_status)
        
        # Agent endpoints
        self.app.router.add_post('/architect/plan', self.handle_architect_plan)
        self.app.router.add_post('/coder/implement', self.handle_coder_implement)
        self.app.router.add_post('/reviewer/review', self.handle_reviewer_review)
        
        # Memory endpoints
        self.app.router.add_get('/memory/search', self.handle_memory_search)
        self.app.router.add_get('/memory/entry/{key}', self.handle_memory_get)
        
        # State endpoints
        self.app.router.add_get('/state', self.handle_get_state)
        self.app.router.add_post('/state', self.handle_update_state)
    
    async def start(self) -> None:
        """Start the server."""
        host = self.config.get('server.host', '127.0.0.1')
        port = self.config.get('server.port', 3000)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Server started at http://{host}:{port}")
        
        # Keep the server running
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    
    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle the root endpoint."""
        return web.json_response({
            "name": "Sochen",
            "version": "0.1.0",
            "status": "operational"
        })
    
    async def handle_status(self, request: web.Request) -> web.Response:
        """Handle the status endpoint."""
        return web.json_response({
            "status": "operational",
            "agents": {
                "architect": "ready",
                "coder": "ready",
                "reviewer": "ready"
            },
            "memory": {
                "entries": len(self.memory.memory)
            },
            "state": {
                "project": self.state.get("project_name", "Unknown"),
                "active": self.state.get("is_active", False)
            }
        })
    
    async def handle_architect_plan(self, request: web.Request) -> web.Response:
        """Handle the architect plan endpoint."""
        try:
            data = await request.json()
            requirements = data.get("requirements", "")
            
            if not requirements:
                return web.json_response({"error": "Requirements are required"}, status=400)
            
            plan = await self.architect.plan_architecture(requirements)
            return web.json_response({"success": True, "plan": plan})
        except Exception as e:
            logger.error(f"Error in architect plan: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_coder_implement(self, request: web.Request) -> web.Response:
        """Handle the coder implement endpoint."""
        try:
            data = await request.json()
            spec = data.get("spec", {})
            path = data.get("path", "")
            
            if not spec or not path:
                return web.json_response({"error": "Spec and path are required"}, status=400)
            
            implemented_path = await self.coder.implement_component(spec, path)
            return web.json_response({
                "success": True,
                "path": implemented_path
            })
        except Exception as e:
            logger.error(f"Error in coder implement: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_reviewer_review(self, request: web.Request) -> web.Response:
        """Handle the reviewer review endpoint."""
        try:
            data = await request.json()
            path = data.get("path", "")
            
            if not path:
                return web.json_response({"error": "Path is required"}, status=400)
            
            review = await self.reviewer.review_code(path)
            return web.json_response({
                "success": True,
                "review": review
            })
        except Exception as e:
            logger.error(f"Error in reviewer review: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_memory_search(self, request: web.Request) -> web.Response:
        """Handle the memory search endpoint."""
        query = request.query.get("q", "")
        limit = int(request.query.get("limit", "5"))
        
        results = self.memory.search(query, limit)
        return web.json_response({"results": results})
    
    async def handle_memory_get(self, request: web.Request) -> web.Response:
        """Handle the memory get endpoint."""
        key = request.match_info["key"]
        entry = self.memory.get_entry(key)
        
        if entry is None:
            return web.json_response({"error": "Entry not found"}, status=404)
        
        return web.json_response({"key": key, "data": entry})
    
    async def handle_get_state(self, request: web.Request) -> web.Response:
        """Handle the get state endpoint."""
        return web.json_response(self.state.get_all())
    
    async def handle_update_state(self, request: web.Request) -> web.Response:
        """Handle the update state endpoint."""
        try:
            data = await request.json()
            for key, value in data.items():
                self.state.set(key, value)
            
            return web.json_response({"success": True, "state": self.state.get_all()})
        except Exception as e:
            logger.error(f"Error updating state: {e}")
            return web.json_response({"error": str(e)}, status=500)
