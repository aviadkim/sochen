"""
State management for the Sochen system.
"""
import logging
import json
import os
from typing import Dict, Any, Optional, TypedDict, List, Union
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class CodeFile(TypedDict):
    """Represents a code file in the project."""
    file_path: str
    content: str
    language: str

class CodeChange(TypedDict):
    """Represents a change to a code file."""
    file_path: str
    original_content: str
    new_content: str
    description: str

class TestResult(TypedDict):
    """Represents the result of a test."""
    test_name: str
    passed: bool
    message: Optional[str]

class SecurityIssue(TypedDict):
    """Represents a security issue."""
    file_path: str
    line_number: int
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    recommendation: str

class CodeIssue(TypedDict):
    """Represents a code quality issue."""
    file_path: str
    line_number: int
    issue_type: str  # "STYLE", "PERFORMANCE", "MAINTAINABILITY", "BUG"
    description: str
    recommendation: str

class AgentAction(Enum):
    """Possible actions an agent can take."""
    ANALYZE = "analyze"
    GENERATE = "generate"
    MODIFY = "modify"
    REVIEW = "review"
    TEST = "test"
    DOCUMENT = "document"
    ASK_HUMAN = "ask_human"

class WorkflowStep(TypedDict):
    """Represents a step in the workflow."""
    agent: str
    action: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]]
    timestamp: float

class AgentStateDict(TypedDict):
    """The shared state passed between agents."""
    # Input data
    task: str  # The overall task or user request
    file_paths: List[str]  # Paths to relevant files
    focused_file_path: Optional[str]  # Currently focused file
    
    # File data
    files: Dict[str, CodeFile]  # Map of file paths to CodeFile objects
    
    # Analysis results
    code_issues: List[CodeIssue]
    security_issues: List[SecurityIssue]
    test_results: List[TestResult]
    
    # Agent outputs and changes
    proposed_changes: List[CodeChange]
    accepted_changes: List[CodeChange]
    
    # Workflow tracking
    current_agent: str
    next_agent: Optional[str]
    workflow_history: List[WorkflowStep]
    
    # Communication
    messages: List[Dict[str, Any]]  # Messages between agents or to/from human
    
    # Error handling
    error: Optional[str]
    
    # Status tracking
    status: str  # "RUNNING", "COMPLETED", "ERROR", "WAITING_FOR_HUMAN"

class AgentState:
    """
    Manages shared state for the agent system.
    Provides persistence and access to shared variables.
    """
    
    def __init__(self, state_file: str = ".state.json"):
        """
        Initialize the state manager.
        
        Args:
            state_file: Path to the state file
        """
        self.state_file = state_file
        self.state = {}
        self.load_state()
        
        # Initialize with default values if state is empty
        if not self.state:
            self.state = {
                "project_name": "default",
                "created_at": datetime.now().isoformat(),
                "is_active": False,
                "current_task": None,
                "environment": {
                    "os": os.name,
                    "python_version": ".".join(map(str, os.sys.version_info[:3]))
                },
                # Initialize the agent state fields
                "task": "",
                "file_paths": [],
                "focused_file_path": None,
                "files": {},
                "code_issues": [],
                "security_issues": [],
                "test_results": [],
                "proposed_changes": [],
                "accepted_changes": [],
                "current_agent": "",
                "next_agent": None,
                "workflow_history": [],
                "messages": [],
                "error": None,
                "status": "WAITING_FOR_HUMAN"
            }
            self.save_state()
        
        logger.info("State manager initialized")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value.
        
        Args:
            key: State key
            default: Default value if key is not found
            
        Returns:
            The state value or default
        """
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a state value.
        
        Args:
            key: State key
            value: Value to set
        """
        self.state[key] = value
        self.state["updated_at"] = datetime.now().isoformat()
        self.save_state()
        logger.debug(f"State updated: {key}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all state variables.
        
        Returns:
            Dictionary with all state variables
        """
        return self.state.copy()
    
    def update(self, values: Dict[str, Any]) -> None:
        """
        Update multiple state values at once.
        
        Args:
            values: Dictionary of key-value pairs to update
        """
        self.state.update(values)
        self.state["updated_at"] = datetime.now().isoformat()
        self.save_state()
        logger.debug(f"State updated with {len(values)} values")
    
    def load_state(self) -> None:
        """Load state from the state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded state from {self.state_file}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def save_state(self) -> None:
        """Save state to the state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    # Additional helper methods for the agent state
    
    def add_file(self, file_path: str, content: str, language: str) -> None:
        """Add or update a file in the state."""
        if "files" not in self.state:
            self.state["files"] = {}
            
        self.state["files"][file_path] = {
            "file_path": file_path,
            "content": content,
            "language": language
        }
        self.save_state()
        logger.debug(f"Added file to state: {file_path}")
    
    def add_code_issue(self, issue: CodeIssue) -> None:
        """Add a code issue to the state."""
        if "code_issues" not in self.state:
            self.state["code_issues"] = []
        
        self.state["code_issues"].append(issue)
        self.save_state()
        logger.debug(f"Added code issue: {issue['description']}")
    
    def add_security_issue(self, issue: SecurityIssue) -> None:
        """Add a security issue to the state."""
        if "security_issues" not in self.state:
            self.state["security_issues"] = []
        
        self.state["security_issues"].append(issue)
        self.save_state()
        logger.debug(f"Added security issue: {issue['description']}")
    
    def add_proposed_change(self, change: CodeChange) -> None:
        """Add a proposed code change to the state."""
        if "proposed_changes" not in self.state:
            self.state["proposed_changes"] = []
        
        self.state["proposed_changes"].append(change)
        self.save_state()
        logger.debug(f"Added proposed change for: {change['file_path']}")
    
    def accept_change(self, index: int) -> None:
        """Accept a proposed change by moving it to accepted changes."""
        if "proposed_changes" not in self.state or index >= len(self.state["proposed_changes"]):
            logger.error(f"Cannot accept change: Invalid index {index}")
            return
        
        if "accepted_changes" not in self.state:
            self.state["accepted_changes"] = []
        
        change = self.state["proposed_changes"].pop(index)
        self.state["accepted_changes"].append(change)
        self.save_state()
        logger.debug(f"Accepted change for: {change['file_path']}")
    
    def add_workflow_step(self, agent: str, action: str, input_data: Dict[str, Any], 
                          output_data: Optional[Dict[str, Any]] = None) -> None:
        """Add a workflow step to the history."""
        if "workflow_history" not in self.state:
            self.state["workflow_history"] = []
        
        step = {
            "agent": agent,
            "action": action,
            "input": input_data,
            "output": output_data,
            "timestamp": datetime.now().timestamp()
        }
        
        self.state["workflow_history"].append(step)
        self.save_state()
        logger.debug(f"Added workflow step: {agent} - {action}")
    
    def set_status(self, status: str) -> None:
        """Set the current status of the agent system."""
        self.state["status"] = status
        self.save_state()
        logger.info(f"Status set to: {status}")
    
    def set_current_agent(self, agent: str) -> None:
        """Set the currently active agent."""
        self.state["current_agent"] = agent
        self.save_state()
        logger.debug(f"Current agent set to: {agent}")
    
    def set_next_agent(self, agent: Optional[str]) -> None:
        """Set the next agent to be activated."""
        self.state["next_agent"] = agent
        self.save_state()
        logger.debug(f"Next agent set to: {agent if agent else 'None'}")
