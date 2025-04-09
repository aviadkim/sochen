"""
Dependency graph for tracking relationships between code artifacts.
"""
from typing import Dict, List, Any, Optional, Set
import logging
import json
import os

logger = logging.getLogger(__name__)

class DependencyGraph:
    """
    Graph representation of code artifacts and their dependencies.
    Used to track relationships between files, functions, classes, etc.
    """
    
    def __init__(self, storage_path: str = ".graph"):
        """
        Initialize the dependency graph.
        
        Args:
            storage_path: Path to store the graph data
        """
        self.storage_path = storage_path
        self.nodes = {}  # id -> node
        self.edges = {}  # from_id -> {to_id -> edge}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_graph()
        
        logger.info("Dependency graph initialized")
    
    def add_node(self, node_id: str, node_type: str, metadata: Dict[str, Any]) -> None:
        """
        Add a node to the graph.
        
        Args:
            node_id: Unique identifier for the node
            node_type: Type of node (file, function, class, etc.)
            metadata: Additional information about the node
        """
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "metadata": metadata
        }
        
        if node_id not in self.edges:
            self.edges[node_id] = {}
        
        logger.debug(f"Added node: {node_id} ({node_type})")
        self._save_graph()
    
    def add_edge(self, from_id: str, to_id: str, edge_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an edge between two nodes.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            edge_type: Type of relationship
            metadata: Additional information about the relationship
        """
        if from_id not in self.nodes or to_id not in self.nodes:
            logger.warning(f"Cannot add edge: nodes {from_id} or {to_id} don't exist")
            return
        
        if from_id not in self.edges:
            self.edges[from_id] = {}
        
        self.edges[from_id][to_id] = {
            "type": edge_type,
            "metadata": metadata or {}
        }
        
        logger.debug(f"Added edge: {from_id} -> {to_id} ({edge_type})")
        self._save_graph()
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node identifier
            
        Returns:
            Node data or None if not found
        """
        return self.nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        Get all nodes of a specific type.
        
        Args:
            node_type: Type of nodes to retrieve
            
        Returns:
            List of matching nodes
        """
        return [node for node in self.nodes.values() if node["type"] == node_type]
    
    def get_dependencies(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies of a node (outgoing edges).
        
        Args:
            node_id: Node identifier
            
        Returns:
            List of nodes that the specified node depends on
        """
        if node_id not in self.edges:
            return []
        
        result = []
        for to_id, edge in self.edges[node_id].items():
            if to_id in self.nodes:
                result.append({
                    "node": self.nodes[to_id],
                    "relationship": edge
                })
        
        return result
    
    def get_dependents(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependents of a node (incoming edges).
        
        Args:
            node_id: Node identifier
            
        Returns:
            List of nodes that depend on the specified node
        """
        result = []
        
        for from_id, edges in self.edges.items():
            if node_id in edges and from_id in self.nodes:
                result.append({
                    "node": self.nodes[from_id],
                    "relationship": edges[node_id]
                })
        
        return result
    
    def get_affected_nodes(self, node_ids: List[str]) -> Set[str]:
        """
        Get all nodes that would be affected by changes to the specified nodes.
        
        Args:
            node_ids: List of node identifiers
            
        Returns:
            Set of node IDs that would be affected
        """
        affected = set(node_ids)
        to_process = list(node_ids)
        
        while to_process:
            current = to_process.pop(0)
            
            # Get immediate dependents
            dependents = [dep["node"]["id"] for dep in self.get_dependents(current)]
            
            # Add new dependents to the affected set and processing queue
            for dep in dependents:
                if dep not in affected:
                    affected.add(dep)
                    to_process.append(dep)
        
        return affected
    
    def _save_graph(self) -> None:
        """Save the graph to disk."""
        try:
            graph_data = {
                "nodes": self.nodes,
                "edges": self.edges
            }
            
            with open(os.path.join(self.storage_path, "graph.json"), 'w') as f:
                json.dump(graph_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
    
    def _load_graph(self) -> None:
        """Load the graph from disk."""
        graph_path = os.path.join(self.storage_path, "graph.json")
        
        if not os.path.exists(graph_path):
            return
        
        try:
            with open(graph_path, 'r') as f:
                graph_data = json.load(f)
                
            self.nodes = graph_data.get("nodes", {})
            self.edges = graph_data.get("edges", {})
            
            logger.info(f"Loaded graph with {len(self.nodes)} nodes and {sum(len(edges) for edges in self.edges.values())} edges")
        except Exception as e:
            logger.error(f"Error loading graph: {e}")

"""
LangGraph workflow definition for the agent system.
"""
import logging
from typing import Dict, Any
import langgraph as lg
from langgraph.prebuilt import StateGraph, ConditionalNode
from .agents import get_all_agents
from .state import AgentStateDict

logger = logging.getLogger("agent_system.graph")

def create_workflow():
    """Create the LangGraph workflow."""
    
    # Get all available agents
    agents = get_all_agents()
    
    # Define a graph state
    class GraphState(AgentStateDict):
        """
        Represents the state of the graph.
        """
        pass
    
    # Define the nodes (agents)
    nodes = {}
    for agent_name, agent_function in agents.items():
        logger.info(f"Adding node for agent: {agent_name}")
        nodes[agent_name] = agent_function
    
    # Define the edges
    def should_continue(state: GraphState):
        """
        Determines whether the workflow should continue or terminate.
        """
        next_agent = state.get("next_agent")
        if next_agent:
            logger.info(f"Workflow should continue with agent: {next_agent}")
            return next_agent
        else:
            logger.info("Workflow should terminate")
            return "terminate"
    
    # Create a graph
    builder = StateGraph(GraphState)
    
    # Add nodes
    for node_name, node_function in nodes.items():
        builder.add_node(node_name, node_function)
    
    # Add edges
    for node_name in nodes.keys():
        builder.add_conditional_edges(
            node_name,
            should_continue,
            {name: name for name in nodes.keys()} | {"terminate": lg.END}
        )
    
    # Set the entry point
    builder.set_entry_point("orchestrator")
    
    # Build the graph
    graph = builder.build()
    
    logger.info("LangGraph workflow created")
    return graph

# Example usage:
if __name__ == "__main__":
    graph = create_workflow()
    print("Graph created successfully.")
