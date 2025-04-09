"""
Code analysis tools for the agent system.
"""
import re
import logging
import difflib
from typing import List, Dict, Any, Tuple, Optional
from ..state import CodeIssue, SecurityIssue

logger = logging.getLogger("agent_system.tools.code_analysis")

def generate_diff(original_content: str, new_content: str) -> str:
    """Generate a unified diff between two strings.
    
    Args:
        original_content: Original content
        new_content: New content
        
    Returns:
        Unified diff as a string
    """
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines, 
        new_lines, 
        fromfile='original',
        tofile='modified',
        n=3
    )
    
    return ''.join(diff)

def parse_issues_from_review(review_text: str, file_path: str) -> List[CodeIssue]:
    """Parse code issues from a review text using pattern matching.
    
    Args:
        review_text: Review text to parse
        file_path: Path to the file being reviewed
        
    Returns:
        List of CodeIssue objects
    """
    issues = []
    
    # Look for patterns like "Line 42: ..." or "Lines 42-45: ..."
    line_patterns = [
        r"[Ll]ine\s+(\d+):\s*(.*?)(?=\n[Ll]ine|\n\n|$)",
        r"[Ll]ines\s+(\d+)(?:-\d+)?:\s*(.*?)(?=\n[Ll]ine|\n\n|$)"
    ]
    
    for pattern in line_patterns:
        matches = re.finditer(pattern, review_text, re.DOTALL)
        for match in matches:
            line_number = int(match.group(1))
            description = match.group(2).strip()
            
            # Try to determine issue type from keywords
            issue_type = "STYLE"  # Default type
            if any(keyword in description.lower() for keyword in ["error", "bug", "crash", "exception", "incorrect"]):
                issue_type = "BUG"
            elif any(keyword in description.lower() for keyword in ["slow", "optimize", "performance", "efficient"]):
                issue_type = "PERFORMANCE"
            elif any(keyword in description.lower() for keyword in ["maintain", "readability", "clean", "structure"]):
                issue_type = "MAINTAINABILITY"
                
            # Try to extract recommendation
            recommendation = ""
            if "recommend" in description.lower() or "suggest" in description.lower():
                parts = re.split(r"[Ii] (?:recommend|suggest)", description, 1)
                if len(parts) > 1:
                    description = parts[0].strip()
                    recommendation = parts[1].strip()
            
            issues.append({
                "file_path": file_path,
                "line_number": line_number,
                "issue_type": issue_type,
                "description": description,
                "recommendation": recommendation or description
            })
    
    return issues

def parse_security_issues(security_text: str, file_path: str) -> List[SecurityIssue]:
    """Parse security issues from a security review text.
    
    Args:
        security_text: Security review text to parse
        file_path: Path to the file being reviewed
        
    Returns:
        List of SecurityIssue objects
    """
    issues = []
    
    # Look for severity indicators
    severity_patterns = [
        (r"(?:CRITICAL|SEVERE|HIGH RISK).*?(?=\n\n|\n[A-Z]|$)", "CRITICAL"),
        (r"(?:HIGH|MAJOR).*?(?=\n\n|\n[A-Z]|$)", "HIGH"),
        (r"(?:MEDIUM|MODERATE).*?(?=\n\n|\n[A-Z]|$)", "MEDIUM"),
        (r"(?:LOW|MINOR).*?(?=\n\n|\n[A-Z]|$)", "LOW")
    ]
    
    for pattern, severity in severity_patterns:
        matches = re.finditer(pattern, security_text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            issue_text = match.group(0)
            
            # Try to extract line number
            line_match = re.search(r"[Ll]ine\s+(\d+)", issue_text)
            line_number = int(line_match.group(1)) if line_match else 0
            
            # Try to extract description and recommendation
            description = issue_text
            recommendation = ""
            
            rec_match = re.search(r"[Rr]ecommend(?:ation|ed):\s*(.*?)(?=\n\n|$)", issue_text, re.DOTALL)
            if rec_match:
                recommendation = rec_match.group(1).strip()
                # Remove recommendation from description
                description = description.replace(rec_match.group(0), "").strip()
            
            issues.append({
                "file_path": file_path,
                "line_number": line_number,
                "severity": severity,
                "description": description,
                "recommendation": recommendation or "Fix the identified security issue."
            })
    
    return issues

def extract_code_blocks(text: str) -> List[str]:
    """Extract code blocks from markdown-style text.
    
    Args:
        text: Text containing markdown code blocks
        
    Returns:
        List of extracted code blocks
    """
    # Match ```language ... ``` blocks
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', text, re.DOTALL)
    
    # Also match indented code blocks if any
    indented_blocks = re.findall(r'(?<=\n)( {4}|\t)+(.*?)(?=\n\S|\n\n|\n$|$)', text, re.DOTALL)
    for indent, block in indented_blocks:
        # Make sure this is actually a code block by checking it's long enough
        if len(block.strip().splitlines()) > 2:
            code_blocks.append(re.sub(r'^( {4}|\t)+', '', block, flags=re.MULTILINE))
    
    return code_blocks

def apply_change(original: str, change_description: str) -> Optional[str]:
    """Try to apply a change based on a text description.
    
    This is a rudimentary implementation that handles some common change patterns.
    
    Args:
        original: Original code content
        change_description: Description of the change to apply
        
    Returns:
        Modified code content or None if parsing failed
    """
    # If the description contains a full code block, extract and use it
    code_blocks = extract_code_blocks(change_description)
    if code_blocks and len(code_blocks) == 1:
        return code_blocks[0]
    
    # Try to parse line-specific changes
    lines = original.splitlines()
    modified = False
    
    # Look for "Change line X from ... to ..."
    line_changes = re.finditer(
        r"[Cc]hange (?:line|lines) (\d+)(?:-(\d+))? from ['\"]?(.*?)['\"]? to ['\"]?(.*?)['\"]?(?=\n|$)", 
        change_description, 
        re.DOTALL
    )
    
    for match in line_changes:
        start_line = int(match.group(1)) - 1  # 0-indexed
        end_line = int(match.group(2)) - 1 if match.group(2) else start_line
        from_text = match.group(3).strip()
        to_text = match.group(4).strip()
        
        # Verify the line content matches what we're looking for
        if (start_line < len(lines) and from_text in lines[start_line]):
            lines[start_line] = lines[start_line].replace(from_text, to_text)
            modified = True
    
    # Look for "Add X after line Y"
    add_after = re.finditer(
        r"[Aa]dd ['\"]?(.*?)['\"]? after line (\d+)",
        change_description,
        re.DOTALL
    )
    
    for match in add_after:
        text_to_add = match.group(1).strip()
        line_num = int(match.group(2)) - 1  # 0-indexed
        
        if line_num < len(lines):
            lines.insert(line_num + 1, text_to_add)
            modified = True
    
    # Look for "Remove line X"
    remove_line = re.finditer(
        r"[Rr]emove line (\d+)(?:-(\d+))?",
        change_description
    )
    
    for match in remove_line:
        start_line = int(match.group(1)) - 1  # 0-indexed
        end_line = int(match.group(2)) - 1 if match.group(2) else start_line
        
        if start_line < len(lines):
            # Remove the specified lines
            lines = lines[:start_line] + lines[end_line+1:]
            modified = True
    
    return '\n'.join(lines) if modified else None

def parse_imports(content: str, language: str) -> List[str]:
    """Parse import statements from code.
    
    Args:
        content: Code content
        language: Programming language of the code
        
    Returns:
        List of imported modules/packages
    """
    imports = []
    
    if language == "Python":
        # Match import statements (simple)
        import_matches = re.finditer(r'^import\s+([\w\., ]+)', content, re.MULTILINE)
        for match in import_matches:
            modules = match.group(1).split(',')
            for module in modules:
                module = module.strip()
                if ' as ' in module:
                    module = module.split(' as ')[0].strip()
                imports.append(module)
        
        # Match from ... import statements
        from_matches = re.finditer(r'^from\s+([\w\.]+)\s+import\s+([\w\., \*]+)', content, re.MULTILINE)
        for match in from_matches:
            package = match.group(1)
            modules = match.group(2).split(',')
            for module in modules:
                module = module.strip()
                if ' as ' in module:
                    module = module.split(' as ')[0].strip()
                imports.append(f"{package}.{module}")
    
    elif language in ["JavaScript", "TypeScript", "JavaScript React", "TypeScript React"]:
        # Match ES6 imports
        es6_matches = re.finditer(r'import\s+(?:{[^}]*}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        for match in es6_matches:
            imports.append(match.group(1))
        
        # Match require statements
        require_matches = re.finditer(r'(?:const|let|var)\s+(?:\w+|{[^}]*})\s*=\s*require\([\'"]([^\'"]+)[\'"]\)', content)
        for match in require_matches:
            imports.append(match.group(1))
    
    return imports

def extract_functions(content: str, language: str) -> List[Dict[str, Any]]:
    """Extract function definitions from code.
    
    Args:
        content: Code content
        language: Programming language of the code
        
    Returns:
        List of dictionaries with function information
    """
    functions = []
    
    if language == "Python":
        # Match function definitions
        fn_matches = re.finditer(
            r'^(?:async\s+)?def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([^:]+))?\s*:', 
            content, 
            re.MULTILINE
        )
        
        for match in fn_matches:
            name = match.group(1)
            params = match.group(2)
            return_type = match.group(3).strip() if match.group(3) else None
            
            # Extract docstring if present
            fn_start = match.end()
            next_lines = content[fn_start:].splitlines()
            
            docstring = ""
            in_docstring = False
            docstring_lines = []
            
            for i, line in enumerate(next_lines):
                stripped = line.strip()
                
                # Check for docstring start
                if i == 0 and stripped in ['"""', "'''"]:
                    in_docstring = True
                    docstring_delimiter = stripped
                    continue
                elif i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
                    in_docstring = True
                    docstring_delimiter = stripped[:3]
                    docstring_lines.append(stripped[3:])
                    continue
                
                # Process docstring content
                if in_docstring:
                    if stripped.endswith(docstring_delimiter) or stripped == docstring_delimiter:
                        in_docstring = False
                        if stripped != docstring_delimiter:
                            docstring_lines.append(stripped[:-len(docstring_delimiter)])
                        break
                    else:
                        docstring_lines.append(stripped)
                else:
                    break
            
            if docstring_lines:
                docstring = "\n".join(docstring_lines)
            
            functions.append({
                "name": name,
                "params": params,
                "return_type": return_type,
                "docstring": docstring
            })
    
    elif language in ["JavaScript", "TypeScript"]:
        # Match function declarations and expressions
        fn_patterns = [
            # Function declarations
            r'function\s+(\w+)\s*\((.*?)\)\s*{',
            # Arrow functions with explicit name
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>'
        ]
        
        for pattern in fn_patterns:
            fn_matches = re.finditer(pattern, content)
            for match in fn_matches:
                name = match.group(1)
                params = match.group(2)
                
                # Extract JSDoc if present
                fn_start = match.start()
                preceding_lines = content[:fn_start].splitlines()
                
                jsdoc_lines = []
                for i in range(len(preceding_lines) - 1, -1, -1):
                    line = preceding_lines[i].strip()
                    if line == '*/':
                        # Found end of JSDoc, now collect from beginning
                        jsdoc = []
                        for j in range(i - 1, -1, -1):
                            line = preceding_lines[j].strip()
                            if line == '/**':
                                jsdoc.reverse()
                                jsdoc_lines = jsdoc
                                break
                            elif line.startswith('*'):
                                jsdoc.append(line[1:].trip())
                    
                    if jsdoc_lines:
                        break
                
                functions.append({
                    "name": name,
                    "params": params,
                    "docstring": "\n".join(jsdoc_lines) if jsdoc_lines else ""
                })
    
    return functions

def extract_classes(content: str, language: str) -> List[Dict[str, Any]]:
    """Extract class definitions from code.
    
    Args:
        content: Code content
        language: Programming language of the code
        
    Returns:
        List of dictionaries with class information
    """
    classes = []
    
    if language == "Python":
        # Match class definitions
        class_matches = re.finditer(
            r'^class\s+(\w+)(?:\((.*?)\))?\s*:', 
            content, 
            re.MULTILINE
        )
        
        for match in class_matches:
            name = match.group(1)
            inheritance = match.group(2) if match.group(2) else ""
            
            # Extract methods (simplified approach)
            methods = []
            class_start = match.end()
            class_content = content[class_start:]
            
            # Look for method definitions with proper indentation
            method_matches = re.finditer(
                r'^\s+def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([^:]+))?\s*:', 
                class_content, 
                re.MULTILINE
            )
            
            for method_match in method_matches:
                method_name = method_match.group(1)
                params = method_match.group(2)
                return_type = method_match.group(3).strip() if method_match.group(3) else None
                
                methods.append({
                    "name": method_name,
                    "params": params,
                    "return_type": return_type
                })
            
            classes.append({
                "name": name,
                "inheritance": inheritance,
                "methods": methods
            })
    
    elif language in ["JavaScript", "TypeScript"]:
        # Match class declarations
        class_matches = re.finditer(
            r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{', 
            content
        )
        
        for match in class_matches:
            name = match.group(1)
            inheritance = match.group(2) if match.group(2) else ""
            
            # Extract methods (simplified approach)
            methods = []
            class_start = match.end()
            # Find where the class ends (matching braces) - simplified
            brace_count = 1
            class_end = class_start
            
            for i, char in enumerate(content[class_start:], class_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i + 1
                        break
            
            class_content = content[class_start:class_end]
            
            # Look for method definitions
            method_patterns = [
                r'(?:async\s+)?(\w+)\s*\((.*?)\)\s*{',  # Regular methods
                r'get\s+(\w+)\s*\(\)\s*{',  # Getters
                r'set\s+(\w+)\s*\((.*?)\)\s*{'  # Setters
            ]
            
            for pattern in method_patterns:
                method_matches = re.finditer(pattern, class_content)
                for method_match in method_matches:
                    method_name = method_match.group(1)
                    params = method_match.group(2) if len(method_match.groups()) > 1 else ""
                    
                    methods.append({
                        "name": method_name,
                        "params": params
                    })
            
            classes.append({
                "name": name,
                "inheritance": inheritance,
                "methods": methods
            })
    
    return classes

def analyze_code(code: str) -> Dict[str, Any]:
    """
    Analyze code to extract metrics and potential issues.
    
    Args:
        code: Source code to analyze
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "lines_of_code": count_lines(code),
        "complexity_estimate": estimate_complexity(code),
        "functions": extract_functions(code),
        "classes": extract_classes(code),
        "imports": extract_imports(code),
        "potential_issues": find_potential_issues(code)
    }
    
    return analysis

def count_lines(code: str) -> int:
    """Count non-empty lines of code."""
    lines = [line for line in code.split('\n') if line.strip()]
    return len(lines)

def estimate_complexity(code: str) -> float:
    """
    Estimate code complexity based on heuristics.
    Returns a value between 0 (simple) and 1 (complex).
    """
    # This is a simplified heuristic
    complexity = 0.0
    
    # Count control structures
    control_keywords = ['if', 'else', 'for', 'while', 'try', 'catch', 'switch', 'case']
    for keyword in control_keywords:
        pattern = r'\b' + keyword + r'\b'
        matches = re.findall(pattern, code)
        complexity += len(matches) * 0.05
    
    # Count function definitions
    function_matches = re.findall(r'\bdef\s+\w+\s*\(', code)
    complexity += len(function_matches) * 0.03
    
    # Count class definitions
    class_matches = re.findall(r'\bclass\s+\w+', code)
    complexity += len(class_matches) * 0.07
    
    # Nested structures add complexity
    indentation_levels = set([len(line) - len(line.lstrip()) for line in code.split('\n')])
    complexity += len(indentation_levels) * 0.02
    
    # Cap at 1.0
    return min(complexity, 1.0)

def extract_functions(code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from code."""
    # Simple regex for Python functions
    function_pattern = r'def\s+(\w+)\s*\(([^)]*)\)'
    functions = []
    
    for match in re.finditer(function_pattern, code):
        name = match.group(1)
        params = [p.strip() for p in match.group(2).split(',') if p.strip()]
        functions.append({
            "name": name,
            "parameters": params
        })
    
    return functions

def extract_classes(code: str) -> List[Dict[str, Any]]:
    """Extract class definitions from code."""
    # Simple regex for Python classes
    class_pattern = r'class\s+(\w+)(?:\s*\(\s*(\w+)\s*\))?'
    classes = []
    
    for match in re.finditer(class_pattern, code):
        name = match.group(1)
        parent = match.group(2) if match.group(2) else None
        classes.append({
            "name": name,
            "parent": parent
        })
    
    return classes

def extract_imports(code: str) -> List[str]:
    """Extract import statements from code."""
    # Simple regex for Python imports
    import_pattern = r'(?:from\s+(\S+)\s+import\s+(.+)|import\s+(.+))'
    imports = []
    
    for match in re.finditer(import_pattern, code):
        if match.group(3):  # Simple import
            modules = [m.strip() for m in match.group(3).split(',')]
            imports.extend(modules)
        else:  # From import
            module = match.group(1)
            entities = [e.strip() for e in match.group(2).split(',')]
            imports.extend([f"{module}.{entity}" for entity in entities])
    
    return imports

def find_potential_issues(code: str) -> List[Dict[str, Any]]:
    """Find potential issues in the code."""
    issues = []
    
    # Check for TODO/FIXME comments
    todo_pattern = r'#\s*(TODO|FIXME):\s*(.*)'
    for match in re.finditer(todo_pattern, code):
        issues.append({
            "type": "comment",
            "severity": "info",
            "message": f"{match.group(1)}: {match.group(2)}"
        })
    
    # Check for potentially unused imports
    # (This is a simplified check and not completely accurate)
    for imp in extract_imports(code):
        module_name = imp.split('.')[-1]
        if module_name not in code.replace(imp, '', 1):
            issues.append({
                "type": "unused_import",
                "severity": "warning",
                "message": f"Potentially unused import: {imp}"
            })
    
    # Check for very long lines
    for i, line in enumerate(code.split('\n')):
        if len(line) > 100:
            issues.append({
                "type": "long_line",
                "severity": "style",
                "line": i + 1,
                "message": f"Line too long ({len(line)} > 100 characters)"
            })
    
    return issues
