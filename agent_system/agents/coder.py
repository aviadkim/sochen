"""
Coder agent that writes new code based on requirements or modifies existing code.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from ..state import AgentState, WorkflowStep, CodeChange
from ..config import get_llm
from ..memory.vector_store import MemoryStore
from ..tools.file_tools import read_file, write_file, detect_language
from ..tools.code_analysis import generate_diff

logger = logging.getLogger("agent_system.agents.coder")

# Initialize memory store
memory = MemoryStore()

def coder_agent(state: AgentState) -> AgentState:
    """Coder agent that writes new code based on requirements or modifies existing code.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with code changes
    """
    logger.info("Running Coder Agent")
    
    # Record this step in workflow history
    current_time = time.time()
    workflow_step = {
        "agent": "coder",
        "action": "code",
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
    
    # If no focused file is specified, look at the task to determine what we should be working on
    if not focused_file_path:
        logger.info("No focused file provided, analyzing task to determine focus")
        llm = get_llm(temperature=0.1)
        
        file_paths = list(files.keys())
        file_paths_str = "\n".join([f"- {path}" for path in file_paths])
        
        focus_prompt = f"""You are the coder agent. Based on the following task and available files, 
determine which file you should focus on for coding. If no existing file is appropriate, suggest a new file name.

Task: {task}

Available files:
{file_paths_str}

Respond with ONLY the filename you want to focus on, or a new filename if needed.
"""
        try:
            response = llm.invoke(focus_prompt)
            focused_file_path = response.content.strip()
            logger.info(f"Determined focused file: {focused_file_path}")
        except Exception as e:
            logger.error(f"Error determining focused file: {e}")
            return {
                **state,
                "error": f"Coder error: Could not determine focused file: {str(e)}",
                "status": "ERROR",
                "current_agent": "coder",
                "workflow_history": state.get("workflow_history", []) + [workflow_step]
            }
    
    # Get or read the focused file
    focused_file = files.get(focused_file_path)
    if not focused_file and focused_file_path:
        content = read_file(focused_file_path)
        if content is not None:
            language = detect_language(focused_file_path)
            focused_file = {
                "file_path": focused_file_path,
                "content": content,
                "language": language
            }
            files[focused_file_path] = focused_file
    
    # Get LLM for coding
    llm = get_llm(temperature=0.2)  # Slightly higher temperature for coding creativity
    
    # Retrieve relevant memories for context
    memories = memory.get_related_memories(
        text=f"{task} {focused_file_path}",
        k=3,
        agent="coder"
    )
    
    # Prepare coding prompt based on whether we're modifying an existing file or creating a new one
    is_new_file = focused_file is None
    code_issues = [issue for issue in state.get("code_issues", []) 
                  if issue.get("file_path") == focused_file_path]
    security_issues = [issue for issue in state.get("security_issues", [])
                      if issue.get("file_path") == focused_file_path]
    
    # Get recent messages about this file
    relevant_messages = []
    for msg in state.get("messages", []):
        if focused_file_path in msg.get("content", ""):
            relevant_messages.append(f"{msg.get('role')}: {msg.get('content')}")
    
    # Limit to last 3 messages
    relevant_messages = relevant_messages[-3:] if relevant_messages else []
    messages_str = "\n\n".join(relevant_messages)
    
    if is_new_file:
        prompt = f"""You are the coder agent in a team of AI agents that work together to analyze and improve code.
Your job is to write new code based on requirements.

Current task: {task}

You need to create a new file: {focused_file_path}

{messages_str}

{memories}

Please write the complete content for this new file. Follow best practices for the file type and implement the requirements completely.
Include appropriate documentation, error handling, and tests as needed.
"""
    else:
        # Existing file - prepare to modify
        content = focused_file.get("content", "")
        language = focused_file.get("language", "Unknown")
        
        # Format code issues
        issues_str = ""
        if code_issues:
            issues_str += "Code issues to address:\n"
            for issue in code_issues:
                issues_str += f"- Line {issue.get('line_number')}: {issue.get('description')}\n"
        
        if security_issues:
            issues_str += "\nSecurity issues to address:\n"
            for issue in security_issues:
                issues_str += f"- Line {issue.get('line_number')} ({issue.get('severity')}): {issue.get('description')}\n"
        
        prompt = f"""You are the coder agent in a team of AI agents that work together to analyze and improve code.
Your job is to modify existing code to implement requirements or fix issues.

Current task: {task}

File to modify: {focused_file_path} ({language})

{issues_str}

{messages_str}

{memories}

Current file content:
```{language}
{content}
```

Please provide the complete updated file content with your changes. Ensure you:
1. Implement the required changes completely
2. Fix any identified issues
3. Follow best practices for {language}
4. Maintain or improve code readability
5. Add or update documentation as needed

After your changes, briefly explain what you modified and why.
"""
    
    try:
        # Get LLM to write/modify code
        response = llm.invoke(prompt)
        response_text = response.content
        
        # Extract code and explanation
        new_code = ""
        explanation = ""
        
        # Try to separate code from explanation
        if "```" in response_text:
            # Extract code from markdown code blocks
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', response_text, re.DOTALL)
            if code_blocks:
                new_code = code_blocks[0].strip()
                # The explanation is everything after the last code block
                last_block_end = response_text.rfind("```") + 3
                explanation = response_text[last_block_end:].strip()
        else:
            # No code blocks, assume it's all code for a new file, or try to extract explanation
            if "\n\n" in response_text and len(response_text.split("\n\n")) > 1:
                parts = response_text.split("\n\n")
                if len(parts[-1]) < 200:  # Assume last paragraph is explanation if short
                    new_code = "\n\n".join(parts[:-1])
                    explanation = parts[-1]
                else:
                    new_code = response_text
            else:
                new_code = response_text
        
        # If we couldn't extract code properly, use the whole response
        if not new_code:
            new_code = response_text
            explanation = "Changes implemented as requested."
        
        # Save the new/modified file
        if is_new_file:
            files[focused_file_path] = {
                "file_path": focused_file_path,
                "content": new_code,
                "language": detect_language(focused_file_path)
            }
            
            # Record the change
            change = {
                "file_path": focused_file_path,
                "original_content": "",
                "new_content": new_code,
                "description": f"Created new file: {focused_file_path}"
            }
            
            # Write the file to disk
            success = write_file(focused_file_path, new_code)
            if not success:
                logger.warning(f"Failed to write new file {focused_file_path}")
        else:
            original_content = focused_file.get("content", "")
            
            # Update file in state
            files[focused_file_path] = {
                "file_path": focused_file_path,
                "content": new_code,
                "language": detect_language(focused_file_path)
            }
            
            # Generate diff for logging
            diff = generate_diff(original_content, new_code)
            
            # Record the change
            change = {
                "file_path": focused_file_path,
                "original_content": original_content,
                "new_content": new_code,
                "description": explanation
            }
            
            # Write the file to disk
            success = write_file(focused_file_path, new_code)
            if not success:
                logger.warning(f"Failed to write changes to {focused_file_path}")
        
        # Save coding action to memory
        memory.add_memory(
            text=f"Modified {focused_file_path}: {explanation}",
            metadata={
                "agent": "coder",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "code",
                "file": focused_file_path
            }
        )
        
        # Update workflow step with output
        workflow_step["output"] = {
            "file_path": focused_file_path,
            "is_new_file": is_new_file,
            "explanation": explanation
        }
        
        # Return updated state
        return {
            **state,
            "files": files,
            "focused_file_path": focused_file_path,
            "current_agent": "coder",
            "proposed_changes": state.get("proposed_changes", []) + [change],
            "workflow_history": state.get("workflow_history", []) + [workflow_step],
            "messages": state.get("messages", []) + [{
                "role": "coder",
                "content": f"Modified {focused_file_path}: {explanation}"
            }]
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error in coder agent: {e}\n{traceback.format_exc()}")
        return {
            **state,
            "error": f"Coder error: {str(e)}",
            "status": "ERROR",
            "current_agent": "coder",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }