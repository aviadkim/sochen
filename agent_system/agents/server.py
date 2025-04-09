"""
WebSocket server for the agent system.
"""
import asyncio
import json
import logging
import time
import os
from typing import Dict, Any, List, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol
from dotenv import load_dotenv

from .config import WEBSOCKET_HOST, WEBSOCKET_PORT, logger
from .graph import create_graph
from .state import AgentState

# Load environment variables
load_dotenv()

# Create the workflow graph
try:
    app = create_graph()
    logger.info("Agent workflow graph created successfully")
except Exception as e:
    logger.error(f"Failed to create agent workflow graph: {e}")
    app = None

# Set of connected clients
connected_clients: Set[WebSocketServerProtocol] = set()

# Active tasks
active_tasks = {}

async def send_status_update(websocket: WebSocketServerProtocol, message: str, data: Optional[Dict] = None):
    """Send a status update to the client.
    
    Args:
        websocket: WebSocket connection
        message: Status message
        data: Optional data to include
    """
    response = {
        "type": "status",
        "message": message,
        "timestamp": time.time(),
        "data": data or {}
    }
    await websocket.send(json.dumps(response))

async def broadcast_status(message: str, data: Optional[Dict] = None):
    """Broadcast a status message to all connected clients.
    
    Args:
        message: Status message
        data: Optional data to include
    """
    if not connected_clients:
        return
    
    response = {
        "type": "status",
        "message": message,
        "timestamp": time.time(),
        "data": data or {}
    }
    
    message_json = json.dumps(response)
    await asyncio.gather(*[client.send(message_json) for client in connected_clients])

async def run_workflow(state: Dict[str, Any], websocket: Optional[WebSocketServerProtocol] = None):
    """Run the agent workflow with the given state.
    
    Args:
        state: Initial workflow state
        websocket: Optional WebSocket connection for status updates
    
    Returns:
        Final state after workflow execution
    """
    if not app:
        error_msg = "Agent workflow graph is not available"
        logger.error(error_msg)
        if websocket:
            await send_status_update(websocket, error_msg, {"error": True})
        return {"error": error_msg, "status": "ERROR"}
    
    # Initialize state with defaults if not present
    if "workflow_history" not in state:
        state["workflow_history"] = []
    if "messages" not in state:
        state["messages"] = []
    if "status" not in state:
        state["status"] = "RUNNING"
    if "files" not in state:
        state["files"] = {}
    
    workflow_id = state.get("workflow_id", str(time.time()))
    state["workflow_id"] = workflow_id
    
    # Add task to active tasks
    active_tasks[workflow_id] = {
        "state": state,
        "status": "RUNNING",
        "start_time": time.time()
    }
    
    try:
        # Start the workflow
        logger.info(f"Starting workflow {workflow_id}: {state.get('task')}")
        if websocket:
            await send_status_update(websocket, f"Starting workflow: {state.get('task')}")
        
        # Create an event handler to provide updates during workflow execution
        async def on_agent_start(agent_name, state):
            logger.info(f"Agent {agent_name} started for workflow {workflow_id}")
            if websocket:
                await send_status_update(websocket, f"Agent {agent_name} is working...", {
                    "agent": agent_name,
                    "workflow_id": workflow_id
                })
            else:
                await broadcast_status(f"Agent {agent_name} is working...", {
                    "agent": agent_name,
                    "workflow_id": workflow_id
                })
        
        # Run the workflow
        # Note: LangGraph's event handlers would be ideal here, but they're not
        # fully exposed in the public API yet. For now, we'll use state.current_agent
        # to track the current agent in each agent function.
        final_state = await app.ainvoke(state)
        
        # Update active tasks
        active_tasks[workflow_id] = {
            "state": final_state,
            "status": final_state.get("status", "COMPLETED"),
            "end_time": time.time(),
            "start_time": active_tasks[workflow_id]["start_time"]
        }
        
        logger.info(f"Workflow {workflow_id} completed with status: {final_state.get('status')}")
        if websocket:
            await send_status_update(websocket, f"Workflow completed with status: {final_state.get('status')}", {
                "workflow_id": workflow_id,
                "status": final_state.get("status")
            })
        else:
            await broadcast_status(f"Workflow completed with status: {final_state.get('status')}", {
                "workflow_id": workflow_id,
                "status": final_state.get("status")
            })
        
        return final_state
    
    except Exception as e:
        logger.error(f"Error running workflow {workflow_id}: {e}")
        error_state = {
            **state,
            "error": f"Workflow error: {str(e)}",
            "status": "ERROR"
        }
        
        # Update active tasks
        active_tasks[workflow_id] = {
            "state": error_state,
            "status": "ERROR",
            "end_time": time.time(),
            "start_time": active_tasks[workflow_id]["start_time"],
            "error": str(e)
        }
        
        if websocket:
            await send_status_update(websocket, f"Error in workflow: {str(e)}", {
                "workflow_id": workflow_id,
                "error": True
            })
        else:
            await broadcast_status(f"Error in workflow: {str(e)}", {
                "workflow_id": workflow_id,
                "error": True
            })
        
        return error_state

async def handle_client(websocket: WebSocketServerProtocol, path: str):
    """Handle a client connection.
    
    Args:
        websocket: WebSocket connection
        path: Connection path
    """
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"Client connected: {client_id}")
    
    # Add to connected clients
    connected_clients.add(websocket)
    
    try:
        # Send welcome message
        await send_status_update(websocket, "Connected to Agent System Server", {
            "version": "1.0.0",
            "active_workflows": len(active_tasks)
        })
        
        # Process messages
        async for message in websocket:
            try:
                # Parse the message
                data = json.loads(message)
                message_type = data.get("type", "")
                
                logger.info(f"Received {message_type} message from {client_id}")
                
                if message_type == "run_workflow":
                    # Get task and initial state
                    task = data.get("task", "")
                    if not task:
                        await send_status_update(websocket, "Error: No task provided", {"error": True})
                        continue
                    
                    # Initial state
                    initial_state = {
                        "task": task,
                        "workflow_id": data.get("workflow_id", str(time.time())),
                        "focused_file_path": data.get("focused_file_path"),
                        "file_paths": data.get("file_paths", []),
                        "status": "RUNNING",
                        "messages": [],
                        "workflow_history": [],
                        "files": {},
                        "code_issues": [],
                        "security_issues": [],
                        "test_results": [],
                        "proposed_changes": [],
                        "accepted_changes": []
                    }
                    
                    # Run the workflow in a background task
                    asyncio.create_task(run_workflow(initial_state, websocket))
                    
                    await send_status_update(websocket, f"Started workflow for task: {task}", {
                        "workflow_id": initial_state["workflow_id"]
                    })
                
                elif message_type == "get_workflow_status":
                    # Get workflow status
                    workflow_id = data.get("workflow_id")
                    if not workflow_id or workflow_id not in active_tasks:
                        await send_status_update(websocket, "Error: Invalid workflow ID", {"error": True})
                        continue
                    
                    workflow = active_tasks[workflow_id]
                    await send_status_update(websocket, f"Workflow status: {workflow['status']}", {
                        "workflow_id": workflow_id,
                        "status": workflow["status"],
                        "start_time": workflow["start_time"],
                        "end_time": workflow.get("end_time"),
                        "current_agent": workflow["state"].get("current_agent"),
                        "error": workflow["state"].get("error")
                    })
                
                elif message_type == "get_workflow_results":
                    # Get workflow results
                    workflow_id = data.get("workflow_id")
                    if not workflow_id or workflow_id not in active_tasks:
                        await send_status_update(websocket, "Error: Invalid workflow ID", {"error": True})
                        continue
                    
                    workflow = active_tasks[workflow_id]
                    state = workflow["state"]
                    
                    # Prepare a simplified version of the state for sending
                    simplified_state = {
                        "status": state.get("status"),
                        "error": state.get("error"),
                        "current_agent": state.get("current_agent"),
                        "messages": state.get("messages", []),
                        "code_issues": state.get("code_issues", []),
                        "security_issues": state.get("security_issues", []),
                        "test_results": state.get("test_results", []),
                        "proposed_changes": [
                            {
                                "file_path": change.get("file_path"),
                                "description": change.get("description")
                            } for change in state.get("proposed_changes", [])
                        ],
                        "workflow_history": [
                            {
                                "agent": step.get("agent"),
                                "action": step.get("action"),
                                "timestamp": step.get("timestamp")
                            } for step in state.get("workflow_history", [])
                        ]
                    }
                    
                    await websocket.send(json.dumps({
                        "type": "workflow_results",
                        "workflow_id": workflow_id,
                        "state": simplified_state
                    }))
                
                elif message_type == "human_feedback":
                    # Handle human feedback
                    workflow_id = data.get("workflow_id")
                    if not workflow_id or workflow_id not in active_tasks:
                        await send_status_update(websocket, "Error: Invalid workflow ID", {"error": True})
                        continue
                    
                    feedback = data.get("feedback", "")
                    action = data.get("action", "continue")
                    
                    workflow = active_tasks[workflow_id]
                    state = workflow["state"]
                    
                    if state.get("status") != "WAITING_FOR_HUMAN":
                        await send_status_update(websocket, "Error: Workflow is not waiting for human input", {"error": True})
                        continue
                    
                    # Update state with human feedback
                    state["messages"] = state.get("messages", []) + [{
                        "role": "human",
                        "content": feedback
                    }]
                    
                    if action == "continue":
                        state["status"] = "RUNNING"
                        state["next_agent"] = "orchestrator"
                        
                        # Run the updated workflow
                        asyncio.create_task(run_workflow(state, websocket))
                    
                    await send_status_update(websocket, f"Human feedback processed: {action}", {
                        "workflow_id": workflow_id
                    })
                
                else:
                    await send_status_update(websocket, f"Unknown message type: {message_type}", {"error": True})
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {client_id}")
                await send_status_update(websocket, "Error: Invalid JSON", {"error": True})
            
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
                await send_status_update(websocket, f"Server error: {str(e)}", {"error": True})
    
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Client disconnected: {client_id} ({e.code})")
    
    except Exception as e:
        logger.error(f"Unexpected error with client {client_id}: {e}")
    
    finally:
        # Remove from connected clients
        connected_clients.remove(websocket)
        logger.info(f"Client removed: {client_id}")

async def start_server():
    """Start the WebSocket server."""
    logger.info(f"Starting WebSocket server on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    
    try:
        async with websockets.serve(handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT):
            logger.info(f"WebSocket server running at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
            await asyncio.Future()  # Run forever
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")