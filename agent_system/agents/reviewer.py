"""
Reviewer agent that examines code for quality, style, and potential issues.
"""
import logging
import time
import re
from typing import Dict, Any, List, Optional
from ..state import AgentState, WorkflowStep, CodeIssue
from ..config import get_llm
from ..memory.vector_store import MemoryStore
from ..tools.code_analysis import parse_issues_from_review

logger = logging.getLogger("agent_system.agents.reviewer")

# Initialize memory store
memory = MemoryStore()

def reviewer_agent(state: AgentState) -> AgentState:
    """Reviewer agent that examines code for quality, style, and potential issues.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with review comments and identified issues
    """
    logger.info("Running Reviewer Agent")
    
    # Record this step in workflow history
    current_time = time.time()
    workflow_step = {
        "agent": "reviewer",
        "action": "review",
        "input": {
            "task": state.get("task"),
            "focused_file": state.get("focused_file_path")
        },
        "output": None,  # Will be filled later
        "timestamp": current_time
    }
    
    # Get task and focused file
    task = state.get("task", "")
    focused_file_path = state.get("focused_file_path")
    files = state.get("files", {})
    
    # If no focused file is specified, use the most recently changed file
    if not focused_file_path:
        proposed_changes = state.get("proposed_changes", [])
        if proposed_changes:
            focused_file_path = proposed_changes[-1].get("file_path")
            logger.info(f"No focused file specified, using most recently changed file: {focused_file_path}")
    
    # Ensure we have a file to review
    if not focused_file_path or focused_file_path not in files:
        logger.error("No valid file to review")
        return {
            **state,
            "error": "Reviewer error: No valid file to review",
            "status": "ERROR",
            "current_agent": "reviewer",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # Get the focused file
    focused_file = files.get(focused_file_path)
    if not focused_file:
        logger.error(f"File not found in state: {focused_file_path}")
        return {
            **state,
            "error": f"Reviewer error: File not found: {focused_file_path}",
            "status": "ERROR",
            "current_agent": "reviewer",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # Get LLM for review
    llm = get_llm(temperature=0.1)  # Low temperature for consistent reviews
    
    # Retrieve relevant memories for context
    memories = memory.get_related_memories(
        text=f"review {focused_file_path}",
        k=3,
        agent="reviewer"
    )
    
    # Get file content and language
    content = focused_file.get("content", "")
    language = focused_file.get("language", "Unknown")
    
    # Determine if this is a recent change
    is_recent_change = False
    change_description = ""
    for change in state.get("proposed_changes", []):
        if change.get("file_path") == focused_file_path:
            is_recent_change = True
            change_description = change.get("description", "")
            break
    
    # Prepare review prompt
    prompt = f"""You are the reviewer agent in a team of AI agents that work together to analyze and improve code.
Your job is to review code for quality, style, and potential issues.

Current task: {task}

File to review: {focused_file_path} ({language})

{"This file was recently modified with the following changes: " + change_description if is_recent_change else ""}

{memories}

File content:
```{language}
{content}
```

Please review the code for:
1. Code quality and adherence to best practices
2. Style consistency and readability
3. Potential bugs or logical errors
4. Performance concerns
5. Security vulnerabilities
6. Documentation completeness

Format your review as follows:
- For each issue, start with "Line X: " or "Lines X-Y: " to identify the location
- Provide clear explanations of the issue
- Suggest specific improvements

Be thorough but focus on the most important issues. Prioritize issues that could cause bugs or security problems.
"""
    
    try:
        # Get LLM review
        response = llm.invoke(prompt)
        review = response.content
        
        # Parse issues from the review
        code_issues = parse_issues_from_review(review, focused_file_path)
        
        # Save review to memory
        memory.add_memory(
            text=f"Reviewed {focused_file_path}. Found {len(code_issues)} issues.",
            metadata={
                "agent": "reviewer",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "review",
                "file": focused_file_path
            }
        )
        
        # Update workflow step with output
        workflow_step["output"] = {
            "file_path": focused_file_path,
            "issues_found": len(code_issues)
        }
        
        # Return updated state
        return {
            **state,
            "current_agent": "reviewer",
            "code_issues": state.get("code_issues", []) + code_issues,
            "workflow_history": state.get("workflow_history", []) + [workflow_step],
            "messages": state.get("messages", []) + [{
                "role": "reviewer",
                "content": review
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in reviewer agent: {e}")
        return {
            **state,
            "error": f"Reviewer error: {str(e)}",
            "status": "ERROR",
            "current_agent": "reviewer",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }