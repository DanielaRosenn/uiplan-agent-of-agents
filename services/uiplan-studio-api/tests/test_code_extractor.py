import pytest
from pathlib import Path

from app.code_extractor import (
    extract_code_snippet,
    parse_file_structure,
    generate_concept_explanation,
    CodeSnippet,
    FileDefinition,
)


def test_extract_python_function():
    code = 'def hello():\n    return "world"'
    result = extract_code_snippet(code, "hello", language="python")
    assert result is not None
    assert result.snippet == code
    assert result.start_line == 1
    assert result.end_line == 2


def test_extract_python_class():
    code = "class MyClass:\n    def __init__(self):\n        pass"
    result = extract_code_snippet(code, "MyClass", language="python")
    assert result is not None
    assert result.snippet == code
    assert result.start_line == 1
    assert result.end_line == 3


def test_extract_python_function_not_found():
    code = 'def hello():\n    return "world"'
    result = extract_code_snippet(code, "goodbye", language="python")
    assert result is None


def test_parse_python_file_structure():
    code = """def function_one():
    pass

class ClassOne:
    def method(self):
        pass

def function_two():
    return 42
"""
    definitions = parse_file_structure(code, language="python")
    assert len(definitions) == 3
    
    func_one = next(d for d in definitions if d.name == "function_one")
    assert func_one.kind == "function"
    assert func_one.start_line == 1
    assert func_one.end_line == 2
    
    class_one = next(d for d in definitions if d.name == "ClassOne")
    assert class_one.kind == "class"
    assert class_one.start_line == 4
    assert class_one.end_line == 6
    
    func_two = next(d for d in definitions if d.name == "function_two")
    assert func_two.kind == "function"
    assert func_two.start_line == 8
    assert func_two.end_line == 9


def test_parse_typescript_file_structure():
    code = """function greet(name: string): string {
    return `Hello ${name}`;
}

class Person {
    constructor(public name: string) {}
}

export const API_URL = "https://api.example.com";
"""
    definitions = parse_file_structure(code, language="typescript")
    assert len(definitions) >= 2  # At least function and class
    
    names = {d.name for d in definitions}
    assert "greet" in names
    assert "Person" in names


def test_parse_xaml_file_structure():
    xaml = """<Activity>
    <Sequence DisplayName="Main Sequence">
        <WriteLine Text="Hello World" />
    </Sequence>
</Activity>
"""
    definitions = parse_file_structure(xaml, language="xaml")
    assert len(definitions) >= 1
    assert any(d.kind == "sequence" for d in definitions)


def test_generate_concept_explanation_python_function():
    node_data = {
        "type": "source_file",
        "title": "app/utils.py",
        "code": {
            "language": "python",
            "snippet": "def calculate_total(items):\n    return sum(items)",
        },
    }
    definition = FileDefinition(name="calculate_total", kind="function", start_line=1, end_line=2)
    
    explanation = generate_concept_explanation(node_data, definition)
    assert "function" in explanation.lower()
    assert "calculate_total" in explanation
    assert "app/utils.py" in explanation


def test_generate_concept_explanation_python_class():
    node_data = {
        "type": "source_file",
        "title": "models/user.py",
        "code": {
            "language": "python",
            "snippet": "class User:\n    pass",
        },
    }
    definition = FileDefinition(name="User", kind="class", start_line=1, end_line=2)
    
    explanation = generate_concept_explanation(node_data, definition)
    assert "class" in explanation.lower()
    assert "User" in explanation
    assert "models/user.py" in explanation


def test_generate_concept_explanation_typescript():
    node_data = {
        "type": "source_file",
        "title": "components/Button.tsx",
        "code": {
            "language": "typescript",
            "snippet": "export const Button = () => { }",
        },
    }
    definition = FileDefinition(name="Button", kind="function", start_line=1, end_line=1)
    
    explanation = generate_concept_explanation(node_data, definition)
    assert "Button" in explanation
    assert "components/Button.tsx" in explanation
