"""
File system tools for the agent system.
"""
import os
import glob
import logging
from typing import List, Dict, Optional
import pygments
from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound
from ..config import get_project_root

logger = logging.getLogger("agent_system.tools.file")

def detect_language(file_path: str) -> str:
    """Detect the programming language of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        String identifying the programming language
    """
    try:
        lexer = get_lexer_for_filename(file_path)
        return lexer.name
    except ClassNotFound:
        # Fallback to simple extension mapping
        ext = os.path.splitext(file_path)[1].lower()
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript React',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript React',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bat': 'Batch',
            '.ps1': 'PowerShell',
        }
        return language_map.get(ext, 'Unknown')

def read_file(file_path: str) -> Optional[str]:
    """Read a file and return its contents.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File contents as a string, or None if the file couldn't be read
    """
    # If file_path is relative, make it absolute from project root
    if not os.path.isabs(file_path):
        file_path = os.path.join(get_project_root(), file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None

def write_file(file_path: str, content: str) -> bool:
    """Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        True if successful, False otherwise
    """
    # If file_path is relative, make it absolute from project root
    if not os.path.isabs(file_path):
        file_path = os.path.join(get_project_root(), file_path)
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False

def list_files(
    directory: str = ".", 
    pattern: str = "*.*", 
    ignore_dirs: List[str] = None, 
    ignore_patterns: List[str] = None
) -> List[str]:
    """List files in a directory matching a pattern.
    
    Args:
        directory: Directory to search in (relative to project root)
        pattern: Glob pattern to match files
        ignore_dirs: List of directory names to ignore
        ignore_patterns: List of patterns to ignore
        
    Returns:
        List of matching file paths
    """
    if ignore_dirs is None:
        ignore_dirs = [".git", ".github", "node_modules", "venv", "__pycache__", ".agent_memory"]
    
    if ignore_patterns is None:
        ignore_patterns = ["*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.class"]
    
    # Make directory absolute from project root
    if not os.path.isabs(directory):
        directory = os.path.join(get_project_root(), directory)
    
    # Find files matching the pattern
    matches = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
    
    # Filter out ignored directories and patterns
    filtered = []
    for path in matches:
        # Skip directories
        if os.path.isdir(path):
            continue
        
        # Check if file is in an ignored directory
        relative_path = os.path.relpath(path, get_project_root())
        if any(ignored in relative_path.split(os.sep) for ignored in ignore_dirs):
            continue
        
        # Check if file matches an ignored pattern
        if any(glob.fnmatch.fnmatch(os.path.basename(path), ignore_pat) for ignore_pat in ignore_patterns):
            continue
        
        filtered.append(relative_path)
    
    return filtered

def get_file_info(file_path: str) -> Dict:
    """Get information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    # If file_path is relative, make it absolute from project root
    if not os.path.isabs(file_path):
        file_path = os.path.join(get_project_root(), file_path)
    
    try:
        stat = os.stat(file_path)
        language = detect_language(file_path)
        
        return {
            "path": os.path.relpath(file_path, get_project_root()),
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "language": language,
            "exists": True
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {file_path}: {e}")
        return {
            "path": file_path,
            "exists": False,
            "error": str(e)
        }
