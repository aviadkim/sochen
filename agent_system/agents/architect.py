"""
Architect agent that designs system architecture and makes high-level design decisions.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from ..state import AgentStateDict
from ..config import get_llm
from ..memory.memory_store import MemoryStore
from ..tools.file_tools import list_files, read_file, detect_language
from ..tools.code_analysis import parse_imports, extract_functions, extract_classes

logger = logging.getLogger("agent_system.agents.architect")

# Initialize memory store
memory = MemoryStore()

def architect_agent(state: AgentStateDict) -> AgentStateDict:
    """Architect agent that designs system architecture and makes high-level design decisions.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with architecture analysis and recommendations
    """
    logger.info("Running Architect Agent")
    
    # Record this step in workflow history
    current_time = time.time()
    workflow_step = {
        "agent": "architect",
        "action": "design",
        "input": {
            "task": state.get("task"),
            "files": list(state.get("files", {}).keys())
        },
        "output": None,  # Will be filled later
        "timestamp": current_time
    }
    
    # Get task and focused file
    task = state.get("task", "")
    focused_file_path = state.get("focused_file_path")
    files = state.get("files", {})
    
    # Scan project structure if not already done
    if not files and not focused_file_path:
        logger.info("Scanning project structure")
        project_files = list_files(".", "*.py")  # Start with Python files
        project_files += list_files(".", "*.js")
        project_files += list_files(".", "*.ts")
        project_files += list_files(".", "*.jsx")
        project_files += list_files(".", "*.tsx")
        project_files += list_files(".", "*.java")
        # Add more extensions as needed
        
        # Read files content
        for file_path in project_files[:10]:  # Limit to 10 files for initial analysis
            content = read_file(file_path)
            if content:
                language = detect_language(file_path)
                files[file_path] = {
                    "file_path": file_path,
                    "content": content,
                    "language": language
                }
    
    # Get LLM for analysis
    llm = get_llm(temperature=0.1)  # Low temperature for more consistent analysis
    
    # Retrieve relevant memories for context
    memories = memory.get_related_memories(
        text=task,
        k=3,
        agent="architect"
    )
    
    # Analyze code structure
    structure_analysis = {}
    for file_path, file_info in files.items():
        content = file_info.get("content", "")
        language = file_info.get("language", "Unknown")
        
        imports = parse_imports(content, language)
        functions = extract_functions(content, language)
        classes = extract_classes(content, language)
        
        structure_analysis[file_path] = {
            "imports": imports,
            "functions": [f.get("name") for f in functions],
            "classes": [c.get("name") for c in classes],
            "language": language
        }
    
    # Prepare structure summary
    structure_summary = "Project Structure:\n"
    for file_path, analysis in structure_analysis.items():
        structure_summary += f"\n- {file_path} ({analysis.get('language')})\n"
        if analysis.get("classes"):
            structure_summary += f"  Classes: {', '.join(analysis.get('classes'))}\n"
        if analysis.get("functions"):
            # Limit to first 5 functions to keep summary manageable
            funcs = analysis.get("functions")
            structure_summary += f"  Functions: {', '.join(funcs[:5])}"
            if len(funcs) > 5:
                structure_summary += f" and {len(funcs) - 5} more"
            structure_summary += "\n"
        if analysis.get("imports"):
            # Limit to first 5 imports to keep summary manageable
            imports = analysis.get("imports")
            structure_summary += f"  Imports: {', '.join(imports[:5])}"
            if len(imports) > 5:
                structure_summary += f" and {len(imports) - 5} more"
            structure_summary += "\n"
    
    # Create a prompt for architecture analysis
    prompt = f"""You are the architect agent in a team of AI agents that work together to analyze and improve code.
Your job is to analyze the project structure, identify architectural patterns, and make high-level design recommendations.

Current task: {task}

{structure_summary}

{memories}

Based on the above information, please provide:
1. An analysis of the current architecture and design patterns
2. Strengths and weaknesses of the current architecture
3. Recommendations for architectural improvements
4. Suggestions for the next development steps

Respond with a comprehensive architectural analysis. Be specific and practical in your recommendations.
"""
    
    try:
        # Get LLM analysis
        response = llm.invoke(prompt)
        analysis = response.content
        
        # Save analysis to memory
        memory.add_memory(
            text=f"Architecture analysis: {analysis[:500]}...",  # Save a summary
            metadata={
                "agent": "architect",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "analysis"
            }
        )
        
        # Update workflow step with output
        workflow_step["output"] = {
            "analysis_length": len(analysis),
            "structure_files_analyzed": len(structure_analysis)
        }
        
        # Return updated state
        return {
            **state,
            "files": files,
            "current_agent": "architect",
            "workflow_history": state.get("workflow_history", []) + [workflow_step],
            "messages": state.get("messages", []) + [{
                "role": "architect",
                "content": analysis
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in architect agent: {e}")
        return {
            **state,
            "error": f"Architect error: {str(e)}",
            "status": "ERROR",
            "current_agent": "architect",
            "workflow_history": workflow_history + [workflow_step]
        }
