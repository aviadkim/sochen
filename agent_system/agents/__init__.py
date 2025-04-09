"""
Agent definitions for the multi-agent system.
"""
from typing import Dict, Any, List, Callable

# Import all agent functions
from .architect import architect_agent
from .coder import coder_agent
from .reviewer import reviewer_agent
from .tester import tester_agent
from .refactor import refactorer_agent
from .security import security_agent
from .documentation import documentation_agent
from .orchestrator import orchestrator_agent

# Dictionary mapping agent names to their functions
AGENTS = {
    "orchestrator": orchestrator_agent,
    "architect": architect_agent,
    "coder": coder_agent,
    "reviewer": reviewer_agent,
    "tester": tester_agent,
    "refactorer": refactorer_agent,
    "security": security_agent,
    "documentation": documentation_agent
}

# Agent descriptions (for help messages and orchestrator agent reference)
AGENT_DESCRIPTIONS = {
    "orchestrator": "Manages the workflow and coordinates other agents.",
    "architect": "Designs system architecture and makes high-level design decisions.",
    "coder": "Writes new code based on requirements or modifies existing code.",
    "reviewer": "Reviews code for quality, style, and potential issues.",
    "tester": "Creates and runs tests to verify code functionality.",
    "refactorer": "Improves code structure and readability without changing functionality.",
    "security": "Analyzes code for security vulnerabilities and suggests improvements.",
    "documentation": "Creates or improves code documentation."
}

# Agent abilities (what each agent can do, for the orchestrator's decision making)
AGENT_ABILITIES = {
    "orchestrator": ["plan", "delegate", "prioritize", "summarize"],
    "architect": ["design", "plan", "evaluate", "advise"],
    "coder": ["implement", "fix", "write", "modify"],
    "reviewer": ["review", "analyze", "critique", "suggest"],
    "tester": ["test", "verify", "validate", "debug"],
    "refactorer": ["refactor", "improve", "optimize", "restructure"],
    "security": ["audit", "identify_vulnerabilities", "secure", "harden"],
    "documentation": ["document", "explain", "comment", "instruct"]
}

def get_all_agents() -> Dict[str, Callable]:
    """Get all available agents.
    
    Returns:
        Dictionary mapping agent names to their functions
    """
    return AGENTS

def get_agent(name: str) -> Callable:
    """Get a specific agent by name.
    
    Args:
        name: Name of the agent
        
    Returns:
        Agent function or None if not found
    """
    return AGENTS.get(name.lower())

def get_agent_description(name: str) -> str:
    """Get the description of an agent.
    
    Args:
        name: Name of the agent
        
    Returns:
        Agent description
    """
    return AGENT_DESCRIPTIONS.get(name.lower(), "No description available")

def get_agent_abilities(name: str) -> List[str]:
    """Get the abilities of an agent.
    
    Args:
        name: Name of the agent
        
    Returns:
        List of agent abilities
    """
    return AGENT_ABILITIES.get(name.lower(), [])
