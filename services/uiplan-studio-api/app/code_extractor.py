import ast
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CodeSnippet:
    """Extracted code snippet with line information."""
    snippet: str
    start_line: int
    end_line: int
    language: str


@dataclass
class FileDefinition:
    """Top-level definition found in a file."""
    name: str
    kind: str  # "function", "class", "sequence", "activity", etc.
    start_line: int
    end_line: int


def extract_code_snippet(code: str, symbol: str, language: str) -> Optional[CodeSnippet]:
    """
    Extract code snippet for a specific function/class/symbol.
    
    Args:
        code: Source code content
        symbol: Name of the symbol to extract (function/class name)
        language: Programming language ("python", "typescript", "xaml")
    
    Returns:
        CodeSnippet if found, None otherwise
    """
    if language == "python":
        return _extract_python_snippet(code, symbol)
    elif language in ("typescript", "tsx"):
        return _extract_typescript_snippet(code, symbol)
    elif language == "xaml":
        return _extract_xaml_snippet(code, symbol)
    
    return None


def parse_file_structure(code: str, language: str) -> list[FileDefinition]:
    """
    Parse file and return list of top-level definitions.
    
    Args:
        code: Source code content
        language: Programming language ("python", "typescript", "xaml")
    
    Returns:
        List of FileDefinition objects for top-level definitions
    """
    if language == "python":
        return _parse_python_structure(code)
    elif language in ("typescript", "tsx"):
        return _parse_typescript_structure(code)
    elif language == "xaml":
        return _parse_xaml_structure(code)
    
    return []


def generate_concept_explanation(node_data: dict, definition: FileDefinition) -> str:
    """
    Generate plain-language explanation for a code definition.
    
    Args:
        node_data: Node metadata including title and code info
        definition: FileDefinition to explain
    
    Returns:
        Human-readable explanation string
    """
    filepath = node_data.get("title", "unknown")
    language = node_data.get("code", {}).get("language", "unknown")
    
    # Simple template-based explanation
    kind_name = definition.kind.capitalize()
    
    if language == "python":
        if definition.kind == "function":
            return f"Python function '{definition.name}' in {filepath}"
        elif definition.kind == "class":
            return f"Python class '{definition.name}' in {filepath}"
    elif language in ("typescript", "tsx"):
        if definition.kind == "function":
            return f"TypeScript function '{definition.name}' in {filepath}"
        elif definition.kind == "class":
            return f"TypeScript class '{definition.name}' in {filepath}"
    elif language == "xaml":
        if definition.kind == "sequence":
            return f"XAML sequence '{definition.name}' in {filepath}"
        elif definition.kind == "activity":
            return f"XAML activity '{definition.name}' in {filepath}"
    
    return f"{kind_name} '{definition.name}' in {filepath}"


# --- Python extraction ---

def _extract_python_snippet(code: str, symbol: str) -> Optional[CodeSnippet]:
    """Extract Python function or class by name."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    
    lines = code.splitlines()
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if node.name == symbol:
                start_line = node.lineno
                end_line = node.end_lineno or node.lineno
                snippet_lines = lines[start_line - 1:end_line]
                snippet = "\n".join(snippet_lines)
                return CodeSnippet(
                    snippet=snippet,
                    start_line=start_line,
                    end_line=end_line,
                    language="python",
                )
    
    return None


def _parse_python_structure(code: str) -> list[FileDefinition]:
    """Parse Python file for top-level functions and classes."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    
    definitions = []
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            definitions.append(FileDefinition(
                name=node.name,
                kind="function",
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
            ))
        elif isinstance(node, ast.AsyncFunctionDef):
            definitions.append(FileDefinition(
                name=node.name,
                kind="function",
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
            ))
        elif isinstance(node, ast.ClassDef):
            definitions.append(FileDefinition(
                name=node.name,
                kind="class",
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
            ))
    
    return definitions


# --- TypeScript extraction ---

def _extract_typescript_snippet(code: str, symbol: str) -> Optional[CodeSnippet]:
    """Extract TypeScript function or class by name using regex."""
    lines = code.splitlines()
    
    # Patterns for function and class declarations
    patterns = [
        rf"^(export\s+)?(async\s+)?function\s+{re.escape(symbol)}\s*[(<]",
        rf"^(export\s+)?class\s+{re.escape(symbol)}\s*[{{<]",
        rf"^(export\s+)?const\s+{re.escape(symbol)}\s*=",
        rf"^(export\s+)?interface\s+{re.escape(symbol)}\s*[{{<]",
    ]
    
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line.strip()):
                # Found the start, now find the end
                start_line = i + 1
                end_line = _find_block_end(lines, i)
                snippet_lines = lines[i:end_line]
                snippet = "\n".join(snippet_lines)
                return CodeSnippet(
                    snippet=snippet,
                    start_line=start_line,
                    end_line=end_line,
                    language="typescript",
                )
    
    return None


def _parse_typescript_structure(code: str) -> list[FileDefinition]:
    """Parse TypeScript file for top-level functions and classes using regex."""
    lines = code.splitlines()
    definitions = []
    
    # Patterns for top-level declarations
    function_pattern = r"^(export\s+)?(async\s+)?function\s+(\w+)"
    class_pattern = r"^(export\s+)?class\s+(\w+)"
    const_pattern = r"^(export\s+)?const\s+(\w+)\s*="
    interface_pattern = r"^(export\s+)?interface\s+(\w+)"
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        match = re.search(function_pattern, stripped)
        if match:
            name = match.group(3)
            start_line = i + 1
            end_line = _find_block_end(lines, i)
            definitions.append(FileDefinition(name=name, kind="function", start_line=start_line, end_line=end_line))
            continue
        
        match = re.search(class_pattern, stripped)
        if match:
            name = match.group(2)
            start_line = i + 1
            end_line = _find_block_end(lines, i)
            definitions.append(FileDefinition(name=name, kind="class", start_line=start_line, end_line=end_line))
            continue
        
        match = re.search(const_pattern, stripped)
        if match:
            name = match.group(2)
            start_line = i + 1
            end_line = _find_statement_end(lines, i)
            definitions.append(FileDefinition(name=name, kind="const", start_line=start_line, end_line=end_line))
            continue
        
        match = re.search(interface_pattern, stripped)
        if match:
            name = match.group(2)
            start_line = i + 1
            end_line = _find_block_end(lines, i)
            definitions.append(FileDefinition(name=name, kind="interface", start_line=start_line, end_line=end_line))
    
    return definitions


def _find_block_end(lines: list[str], start_index: int) -> int:
    """Find the end of a code block (handles braces)."""
    brace_count = 0
    in_block = False
    
    for i in range(start_index, len(lines)):
        line = lines[i]
        
        for char in line:
            if char == "{":
                brace_count += 1
                in_block = True
            elif char == "}":
                brace_count -= 1
                if in_block and brace_count == 0:
                    return i + 1
    
    # If no closing brace found, return next line
    return start_index + 1


def _find_statement_end(lines: list[str], start_index: int) -> int:
    """Find the end of a single statement (ends with semicolon or newline)."""
    for i in range(start_index, len(lines)):
        if ";" in lines[i]:
            return i + 1
    return start_index + 1


# --- XAML extraction ---

def _extract_xaml_snippet(code: str, symbol: str) -> Optional[CodeSnippet]:
    """Extract XAML activity or sequence by DisplayName."""
    try:
        root = ET.fromstring(code)
    except ET.ParseError:
        return None
    
    lines = code.splitlines()
    
    # Search for element with matching DisplayName
    for elem in root.iter():
        display_name = elem.get("DisplayName", "")
        if display_name == symbol or elem.tag.endswith(symbol):
            # Find line number (approximate)
            elem_str = ET.tostring(elem, encoding="unicode")
            for i, line in enumerate(lines):
                if symbol in line or display_name in line:
                    # Simple approximation: extract a few lines
                    start_line = i + 1
                    end_line = min(i + 5, len(lines))
                    snippet = "\n".join(lines[i:end_line])
                    return CodeSnippet(
                        snippet=snippet,
                        start_line=start_line,
                        end_line=end_line,
                        language="xaml",
                    )
    
    return None


def _parse_xaml_structure(code: str) -> list[FileDefinition]:
    """Parse XAML file for sequences and activities."""
    try:
        root = ET.fromstring(code)
    except ET.ParseError:
        return []
    
    definitions = []
    lines = code.splitlines()
    
    # Find Sequence elements
    for elem in root.iter():
        if elem.tag.endswith("Sequence"):
            display_name = elem.get("DisplayName", f"Sequence_{len(definitions)}")
            # Find approximate line number
            for i, line in enumerate(lines):
                if display_name in line or "Sequence" in line:
                    definitions.append(FileDefinition(
                        name=display_name,
                        kind="sequence",
                        start_line=i + 1,
                        end_line=i + 1,
                    ))
                    break
    
    return definitions
