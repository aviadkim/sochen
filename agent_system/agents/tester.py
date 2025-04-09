"""
Tester agent that creates and runs tests to verify code functionality.
"""
import logging
import time
import re
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from ..state import AgentState, WorkflowStep, TestResult
from ..config import get_llm
from ..memory.vector_store import MemoryStore
from ..tools.file_tools import read_file, write_file, detect_language
from ..config import get_project_root

logger = logging.getLogger("agent_system.agents.tester")

# Initialize memory store
memory = MemoryStore()

def run_python_test(test_code: str) -> Tuple[bool, str]:
    """Run a Python test in a temporary file.
    
    Args:
        test_code: Python test code
        
    Returns:
        Tuple of (success, output)
    """
    try:
        # Create a temporary file for the test
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            f.write(test_code)
            temp_file_path = f.name
        
        # Run the test using Python
        result = subprocess.run(
            ['python', temp_file_path],
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Check if the test passed
        success = result.returncode == 0
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        
        return success, output
    
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 10 seconds"
    except Exception as e:
        return False, f"Error running test: {str(e)}"

def run_javascript_test(test_code: str) -> Tuple[bool, str]:
    """Run a JavaScript test in a temporary file using Node.js.
    
    Args:
        test_code: JavaScript test code
        
    Returns:
        Tuple of (success, output)
    """
    try:
        # Create a temporary file for the test
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
            f.write(test_code)
            temp_file_path = f.name
        
        # Run the test using Node.js
        result = subprocess.run(
            ['node', temp_file_path],
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Check if the test passed
        success = result.returncode == 0
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        
        return success, output
    
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 10 seconds"
    except Exception as e:
        return False, f"Error running test: {str(e)}"

def tester_agent(state: AgentState) -> AgentState:
    """Tester agent that creates and runs tests to verify code functionality.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with test results
    """
    logger.info("Running Tester Agent")
    
    # Record this step in workflow history
    current_time = time.time()
    workflow_step = {
        "agent": "tester",
        "action": "test",
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
    
    # Ensure we have a file to test
    if not focused_file_path or focused_file_path not in files:
        logger.error("No valid file to test")
        return {
            **state,
            "error": "Tester error: No valid file to test",
            "status": "ERROR",
            "current_agent": "tester",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # Get the focused file
    focused_file = files.get(focused_file_path)
    if not focused_file:
        logger.error(f"File not found in state: {focused_file_path}")
        return {
            **state,
            "error": f"Tester error: File not found: {focused_file_path}",
            "status": "ERROR",
            "current_agent": "tester",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }
    
    # Get LLM for testing
    llm = get_llm(temperature=0.2)  # Slightly higher temperature for test scenario variety
    
    # Retrieve relevant memories for context
    memories = memory.get_related_memories(
        text=f"test {focused_file_path}",
        k=3,
        agent="tester"
    )
    
    # Get file content and language
    content = focused_file.get("content", "")
    language = focused_file.get("language", "Unknown")
    
    # Prepare test generation prompt
    prompt = f"""You are the tester agent in a team of AI agents that work together to analyze and improve code.
Your job is to create and run tests to verify code functionality.

Current task: {task}

File to test: {focused_file_path} ({language})

{memories}

File content:
```{language}
{content}
```

Please create a comprehensive test for this code that:
1. Tests all key functionality
2. Includes edge cases and error handling tests
3. Is self-contained and runnable

The test should be completely self-contained and not require any external dependencies not included in the standard library.
For classes or functions, include example usage.

For Python, use unittest or simple assertions that can run directly.
For JavaScript, use simple tests with console.assert() or console.log() to indicate success/failure.

Write ONLY the test code without explanation. The test will be executed directly.
"""
    
    try:
        # Get LLM to generate tests
        response = llm.invoke(prompt)
        test_code = response.content
        
        # Extract code block if present
        if "```" in test_code:
            # Extract code from markdown code blocks
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', test_code, re.DOTALL)
            if code_blocks:
                test_code = code_blocks[0].strip()
        
        # Run the tests based on language
        test_results = []
        if language == "Python":
            success, output = run_python_test(test_code)
            test_results.append({
                "test_name": f"Test for {focused_file_path}",
                "passed": success,
                "message": output
            })
        elif language in ["JavaScript", "TypeScript", "JavaScript React", "TypeScript React"]:
            success, output = run_javascript_test(test_code)
            test_results.append({
                "test_name": f"Test for {focused_file_path}",
                "passed": success,
                "message": output
            })
        else:
            # For unsupported languages, just save the test code but don't run it
            test_results.append({
                "test_name": f"Test for {focused_file_path}",
                "passed": None,  # None indicates not run
                "message": f"Tests not run - unsupported language: {language}"
            })
        
        # Save test code to a file
        test_file_path = focused_file_path.rsplit(".", 1)[0] + "_test." + focused_file_path.rsplit(".", 1)[1]
        success = write_file(test_file_path, test_code)
        if success:
            files[test_file_path] = {
                "file_path": test_file_path,
                "content": test_code,
                "language": language
            }
        
        # Format test results for the message
        test_results_str = "Test Results:\n"
        for result in test_results:
            status = "✅ PASSED" if result.get("passed") else "❌ FAILED" if result.get("passed") is False else "⚠️ NOT RUN"
            test_results_str += f"{result.get('test_name')}: {status}\n"
            if result.get("message"):
                # Truncate long output
                message = result.get("message")
                if len(message) > 500:
                    message = message[:500] + "... (truncated)"
                test_results_str += f"Output: {message}\n"
        
        # Save test results to memory
        memory.add_memory(
            text=f"Tested {focused_file_path}. Results: {test_results_str}",
            metadata={
                "agent": "tester",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "test",
                "file": focused_file_path
            }
        )
        
        # Update workflow step with output
        workflow_step["output"] = {
            "file_path": focused_file_path,
            "test_file": test_file_path,
            "results": [result.get("passed") for result in test_results]
        }
        
        # Return updated state
        return {
            **state,
            "files": files,
            "current_agent": "tester",
            "test_results": state.get("test_results", []) + test_results,
            "workflow_history": state.get("workflow_history", []) + [workflow_step],
            "messages": state.get("messages", []) + [{
                "role": "tester",
                "content": test_results_str
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in tester agent: {e}")
        return {
            **state,
            "error": f"Tester error: {str(e)}",
            "status": "ERROR",
            "current_agent": "tester",
            "workflow_history": state.get("workflow_history", []) + [workflow_step]
        }