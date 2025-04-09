"""
Orchestrator agent that coordinates the workflow and decides which agents to invoke.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from ..state import AgentStateDict
from ..config import get_llm
from ..memory.memory_store import MemoryStore

logger = logging.getLogger("agent_system.agents.orchestrator")

# Initialize memory store
memory = MemoryStore()

def orchestrator_agent(state: AgentStateDict) -> AgentStateDict:
    """Orchestrator agent that decides the next step in the workflow.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with the next agent to run
    """
    logger.info("Running Orchestrator Agent")
    
    # Record this step in workflow history
    current_time = time.time()
    workflow_step = {
        "agent": "orchestrator",
        "action": "orchestrate",
        "input": {"task": state.get("task")},
        "output": None,  # Will be filled later
        "timestamp": current_time
    }
    
    # Get task and status
    task = state.get("task", "")
    status = state.get("status", "RUNNING")
    
    # Check for error state
    error = state.get("error")
    if error:
        logger.error(f"Workflow in error state: {error}")
        return {
            **state,
            "next_agent": None,
            "status": "ERROR",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # If we're waiting for human input, stay there
    if status == "WAITING_FOR_HUMAN":
        logger.info("Workflow is waiting for human input")
        return {
            **state,
            "next_agent": None,
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # If we have no more work to do, mark as completed
    if status == "COMPLETED":
        logger.info("Workflow is complete")
        return {
            **state,
            "next_agent": None,
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # Get workflow history
    workflow_history = state.get("workflow_history", [])
    
    # Get LLM for decision making
    llm = get_llm(temperature=0.2)  # Lower temperature for more consistent decisions
    
    # Retrieve relevant memories for context
    memories = memory.get_related_memories(
        text=task,
        k=3,
        agent="orchestrator"
    )
    
    # Create a prompt for deciding the next agent
    current_agent = state.get("current_agent", "orchestrator")
    code_issues = state.get("code_issues", [])
    security_issues = state.get("security_issues", [])
    test_results = state.get("test_results", [])
    proposed_changes = state.get("proposed_changes", [])
    recent_history = workflow_history[-5:] if len(workflow_history) > 5 else workflow_history
    
    # Format recent history
    history_str = ""
    for step in recent_history:
        history_str += f"- Agent: {step.get('agent')}, Action: {step.get('action')}\n"
    
    # Format issues and test results
    issues_str = ""
    if code_issues:
        issues_str += f"Code Issues: {len(code_issues)}\n"
    if security_issues:
        issues_str += f"Security Issues: {len(security_issues)}\n"
    if test_results:
        passed = sum(1 for t in test_results if t.get("passed", False))
        failed = len(test_results) - passed
        issues_str += f"Test Results: {passed} passed, {failed} failed\n"
    if proposed_changes:
        issues_str += f"Proposed Changes: {len(proposed_changes)}\n"
    
    prompt = f"""You are the orchestrator agent in a team of AI agents that work together to analyze and improve code.
Your job is to decide which agent should be activated next based on the current state of the workflow.

Available agents:
- architect: Designs system architecture and makes high-level design decisions.
- coder: Writes new code based on requirements or modifies existing code.
- reviewer: Reviews code for quality, style, and potential issues.
- tester: Creates and runs tests to verify code functionality.
- refactorer: Improves code structure and readability without changing functionality.
- security: Analyzes code for security vulnerabilities and suggests improvements.
- documentation: Creates or improves code documentation.

Current task: {task}

Current agent: {current_agent}

Workflow state:
{issues_str}

Recent workflow history:
{history_str}

{memories}

Based on the above information, determine the next agent that should be activated, or if the workflow should be completed or wait for human input.

Think step by step about what needs to be done next, and justify your choice.

Your response should be in the following format:
REASONING: Your detailed reasoning for choosing the next agent.
NEXT_AGENT: [agent_name or "COMPLETE" or "ASK_HUMAN"]
"""
    
    try:
        # Get LLM decision
        response = llm.invoke(prompt)
        response_text = response.content
        
        # Parse the response
        reasoning = ""
        next_agent = None
        
        if "REASONING:" in response_text and "NEXT_AGENT:" in response_text:
            reasoning_part = response_text.split("NEXT_AGENT:")[0]
            reasoning = reasoning_part.replace("REASONING:", "").strip()
            
            next_agent_part = response_text.split("NEXT_AGENT:")[1].strip().split("\n")[0].strip()
            next_agent = next_agent_part.lower()
        else:
            # Fallback parsing if format wasn't followed
            logger.warning("Orchestrator response format was not as expected, attempting to extract agent name")
            if "architect" in response_text.lower():
                next_agent = "architect"
            elif "coder" in response_text.lower():
                next_agent = "coder"
            elif "reviewer" in response_text.lower():
                next_agent = "reviewer"
            elif "tester" in response_text.lower():
                next_agent = "tester"
            elif "refactorer" in response_text.lower():
                next_agent = "refactorer"
            elif "security" in response_text.lower():
                next_agent = "security"
            elif "documentation" in response_text.lower():
                next_agent = "documentation"
            elif "complete" in response_text.lower():
                next_agent = "COMPLETE"
            elif "ask_human" in response_text.lower() or "human" in response_text.lower():
                next_agent = "ASK_HUMAN"
        
        # Handle special cases
        if next_agent == "COMPLETE":
            logger.info("Orchestrator decided workflow is complete")
            new_status = "COMPLETED"
            next_agent = None
        elif next_agent == "ASK_HUMAN":
            logger.info("Orchestrator decided to ask for human input")
            new_status = "WAITING_FOR_HUMAN"
            next_agent = None
        else:
            logger.info(f"Orchestrator selected next agent: {next_agent}")
            new_status = "RUNNING"
        
        # Save reasoning to memory
        memory.add_memory(
            text=f"Decided next agent should be {next_agent} because: {reasoning}",
            metadata={
                "agent": "orchestrator",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "decision"
            }
        )
        
        # Update workflow step with output
        workflow_step["output"] = {
            "next_agent": next_agent,
            "reasoning": reasoning
        }
        
        # Return updated state
        return {
            **state,
            "next_agent": next_agent,
            "status": new_status,
            "current_agent": "orchestrator",
            "workflow_history": state.get("workflow_history", []) + [workflow_step],
            "messages": state.get("messages", []) + [{
                "role": "orchestrator",
                "content": f"Next step: {reasoning}"
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in orchestrator agent: {e}")
        return {
            **state,
            "error": f"Orchestrator error: {str(e)}",
            "status": "ERROR",
            "next_agent": None,
            "workflow_history": workflow_history + [workflow_step]
        }
