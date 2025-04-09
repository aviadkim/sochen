"""
Graph definition for the agent system workflow.
"""
import logging
from typing import Dict, Any, List, Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import get_agent, get_all_agents

logger = logging.getLogger("agent_system.graph")

# Initialize the state graph with the AgentState type
def create_graph() -> StateGraph:
    """Create the agent workflow graph.
    
    Returns:
        Compiled StateGraph for the agent workflow
    """
    # Create a new graph
    workflow = StateGraph(AgentState)
    
    # Add nodes for each agent
    agents = get_all_agents()
    for agent_name, agent_func in agents.items():
        workflow.add_node(agent_name, agent_func)
    
    # Define the entry point: always start with the orchestrator
    workflow.set_entry_point("orchestrator")
    
    # Define the conditional edges
    def route_agent(state: AgentState) -> Dict[str, Any]:
        """Route to the next agent based on state.next_agent."""
        next_agent = state.get("next_agent")
        error = state.get("error")
        status = state.get("status")
        
        # If there's an error or we're completed/waiting, end the workflow
        if error or status in ["COMPLETED", "WAITING_FOR_HUMAN"]:
            return {"next": END}
        
        # If next_agent is None or invalid, default to orchestrator
        if not next_agent or next_agent not in agents:
            return {"next": "orchestrator"}
            
        # Otherwise, route to the specified next agent
        return {"next": next_agent}
    
    # Add conditional edges from each agent
    for agent_name in agents:
        workflow.add_conditional_edges(
            agent_name,
            route_agent,
            {
                "next": list(agents.keys()) + [END]
            }
        )
    
    # Compile the graph
    return workflow.compile()