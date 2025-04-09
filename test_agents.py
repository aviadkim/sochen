"""
Simple test script for the agent system.
"""
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Ensure the agent_system module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Load environment variables from .env file
load_dotenv()

# Import agent system
from agent_system.server import run_workflow
from agent_system.config import logger
from agent_system.state import AgentStateDict

async def test_specific_agent(agent_name: str, task: str) -> None:
    """Test a specific agent with a simple task.
    
    Args:
        agent_name: Name of the agent to test
        task: Task description
    """
    logger.info(f"Testing {agent_name} agent with task: {task}")
    
    # Create a simple test file if needed
    test_file_path = "test_sample.py"
    test_file_content = "# Sample file for testing\n\ndef hello_world():\n    print('Hello, World!')\n"
    if agent_name in ["coder", "reviewer", "tester"]:
        with open(test_file_path, "w") as f:
            f.write(test_file_content)
        
        initial_state: AgentStateDict = {
            "task": task,
            "focused_file_path": test_file_path,
            "files": {
                test_file_path: {
                    "file_path": test_file_path,
                    "content": test_file_content,
                    "language": "Python"
                }
            },
            "status": "RUNNING",
            "current_agent": agent_name,
            "next_agent": None,
            "messages": [],
            "workflow_history": [],
            "code_issues": [],
            "security_issues": [],
            "test_results": [],
            "proposed_changes": [],
            "accepted_changes": [],
            "error": None  # Initialize error to None
        }
    else:
        initial_state: AgentStateDict = {
            "task": task,
            "status": "RUNNING",
            "current_agent": agent_name,
            "next_agent": None,
            "messages": [],
            "workflow_history": [],
            "files": {},
            "code_issues": [],
            "security_issues": [],
            "test_results": [],
            "proposed_changes": [],
            "accepted_changes": [],
            "focused_file_path": None,  # Add focused_file_path
            "error": None  # Initialize error to None
        }
    
    # Run the workflow
    final_state: AgentStateDict = await run_workflow(initial_state)
    
    # Print results
    print("\n--- TEST RESULTS ---\n")
    print(f"Task: {task}")
    print(f"Agent: {agent_name}")
    print(f"Status: {final_state.get('status')}")
    
    if final_state.get("error"):
        print(f"Error: {final_state.get('error')}")
    
    print("\nMessages:")
    for msg in final_state.get("messages", []):
        print(f"- {msg.get('role')}: {msg.get('content')[:100]}..." if len(msg.get('content', '')) > 100 else f"- {msg.get('role')}: {msg.get('content')}")
    
    # Save the full state to a file for detailed inspection
    with open(f"test_{agent_name}_results.json", "w") as f:
        # Convert state to JSON-serializable form
        serializable_state = {
            k: (str(v) if isinstance(v, list) or isinstance(v, dict) else v)
            for k, v in final_state.items()
        }
        json.dump(serializable_state, f, indent=2)
    
    print(f"\nFull results saved to test_{agent_name}_results.json")

async def test_full_workflow(task: str) -> None:
    """Test the full agent workflow with orchestration.
    
    Args:
        task: Task description
    """
    logger.info(f"Testing full workflow with task: {task}")
    
    # Create a sample file
    test_file_path = "test_sample.py"
    test_file_content = "# Sample file for testing\n\ndef hello_world():\n    print('Hello, World!')\n"
    with open(test_file_path, "w") as f:
        f.write(test_file_content)
    
    # Initial state
    initial_state: AgentStateDict = {
        "task": task,
        "focused_file_path": test_file_path,
        "files": {
            test_file_path: {
                "file_path": test_file_path,
                "content": test_file_content,
                "language": "Python"
            }
        },
        "status": "RUNNING",
        "current_agent": "orchestrator",  # Start with orchestrator
        "next_agent": None,
        "messages": [],
        "workflow_history": [],
        "code_issues": [],
        "security_issues": [],
        "test_results": [],
        "proposed_changes": [],
        "accepted_changes": [],
        "error": None  # Initialize error to None
    }
    
    # Run the workflow
    final_state: AgentStateDict = await run_workflow(initial_state)
    
    # Print results
    print("\n--- FULL WORKFLOW RESULTS ---\n")
    print(f"Task: {task}")
    print(f"Status: {final_state.get('status')}")
    
    if final_state.get("error"):
        print(f"Error: {final_state.get('error')}")
    
    print("\nWorkflow History:")
    for step in final_state.get("workflow_history", []):
        print(f"- Agent: {step.get('agent')}, Action: {step.get('action')}")
    
    print("\nMessages:")
    for msg in final_state.get("messages", []):
        print(f"- {msg.get('role')}: {msg.get('content')[:100]}..." if len(msg.get('content', '')) > 100 else f"- {msg.get('role')}: {msg.get('content')}")
    
    # Save the full state to a file for detailed inspection
    with open("test_full_workflow_results.json", "w") as f:
        # Convert state to JSON-serializable form
       serializable_state = {
            k: (str(v) if isinstance(v, list) or isinstance(v, dict) else v)
            for k, v in final_state.items()
        }
        json.dump(serializable_state, f, indent=2)
    
    print("\nFull results saved to test_full_workflow_results.json")

async def main():
    """Main test function."""
    print("AI Agent System - Test Script")
    print("============================\n")
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set")
        print("Please set it in your .env file or environment variables")
        return
    
    # Prompt for test type
    print("Select a test to run:")
    print("1. Test Coder agent")
    print("2. Test Reviewer agent")
    print("3. Test Tester agent")
    print("4. Test Orchestrator agent")
    print("5. Test full workflow")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == "1":
        task = input("Enter a coding task (e.g., 'Add docstring to hello_world function'): ")
        await test_specific_agent("coder", task)
    elif choice == "2":
        task = input("Enter a review task (e.g., 'Review code for style issues'): ")
        await test_specific_agent("reviewer", task)
    elif choice == "3":
        task = input("Enter a testing task (e.g., 'Write tests for hello_world function'): ")
        await test_specific_agent("tester", task)
    elif choice == "4":
        task = input("Enter a task for orchestration (e.g., 'Improve the hello_world function'): ")
        await test_specific_agent("orchestrator", task)
    elif choice == "5":
        task = input("Enter a task for full workflow (e.g., 'Improve the hello_world function'): ")
        await test_full_workflow(task)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest script stopped by user")
    except Exception as e:
        print(f"Error in test script: {e}")