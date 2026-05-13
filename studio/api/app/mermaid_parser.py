"""Extract Mermaid diagrams from markdown files by heading anchor.

Supports `file.md#anchor` references that point at a Mermaid code block under
a specific heading. Returns raw Mermaid source and basic node/edge extraction
for flowchart and sequenceDiagram types.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MermaidBlock:
    """A parsed Mermaid diagram block."""
    source: str  # Raw mermaid source
    diagram_type: str  # flowchart | sequenceDiagram | stateDiagram | etc
    nodes: list[MermaidNode]
    edges: list[MermaidEdge]


@dataclass(frozen=True)
class MermaidNode:
    """A node extracted from Mermaid source."""
    id: str
    label: str
    shape: str  # rectangle | rounded | diamond | cylinder | circle | etc
    class_name: str | None = None  # CSS class from classDef


@dataclass(frozen=True)
class MermaidEdge:
    """An edge extracted from Mermaid source."""
    source: str
    target: str
    label: str | None = None
    style: str | None = None  # solid | dashed | dotted


def extract_mermaid_block(
    file_path: Path,
    anchor: str | None = None,
) -> MermaidBlock | None:
    """Extract a Mermaid block from a markdown file.
    
    Args:
        file_path: Path to the markdown file
        anchor: Heading anchor (e.g. "solution-architecture"). If None, returns
                the first Mermaid block in the file.
    
    Returns:
        Parsed MermaidBlock or None if not found.
    """
    if not file_path.exists():
        return None
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    
    if anchor:
        # Find the heading and extract the next Mermaid block after it
        heading_pattern = rf"^#+\s+.*?{re.escape(anchor.replace('-', ' '))}.*?$"
        lines = content.splitlines()
        heading_idx = None
        
        for i, line in enumerate(lines):
            if re.search(heading_pattern, line, re.IGNORECASE):
                heading_idx = i
                break
        
        if heading_idx is None:
            return None
        
        # Find the next ```mermaid block after the heading
        mermaid_start = None
        for i in range(heading_idx + 1, len(lines)):
            if lines[i].strip().startswith("```mermaid"):
                mermaid_start = i + 1
                break
        
        if mermaid_start is None:
            return None
        
        # Extract until closing ```
        mermaid_lines = []
        for i in range(mermaid_start, len(lines)):
            if lines[i].strip() == "```":
                break
            mermaid_lines.append(lines[i])
        
        mermaid_source = "\n".join(mermaid_lines)
    else:
        # Find first ```mermaid block
        pattern = r"```mermaid\n(.*?)\n```"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return None
        mermaid_source = match.group(1)
    
    if not mermaid_source.strip():
        return None
    
    return _parse_mermaid_source(mermaid_source)


def _parse_mermaid_source(source: str) -> MermaidBlock:
    """Parse Mermaid source into nodes and edges.
    
    Basic extraction for flowchart and sequenceDiagram. Does not handle all
    Mermaid syntax — just enough to seed AS-IS/TO-BE canvases.
    """
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    
    # Detect diagram type
    diagram_type = "flowchart"
    if lines and lines[0].startswith("sequenceDiagram"):
        diagram_type = "sequenceDiagram"
    elif lines and lines[0].startswith("stateDiagram"):
        diagram_type = "stateDiagram"
    elif lines and lines[0].startswith("flowchart"):
        diagram_type = "flowchart"
    
    nodes: list[MermaidNode] = []
    edges: list[MermaidEdge] = []
    node_classes: dict[str, str] = {}  # node_id -> class_name
    
    if diagram_type == "flowchart":
        nodes, edges, node_classes = _parse_flowchart(lines)
    elif diagram_type == "sequenceDiagram":
        nodes, edges = _parse_sequence(lines)
    
    # Apply classes to nodes
    for node in nodes:
        if node.id in node_classes:
            nodes = [
                MermaidNode(
                    id=n.id,
                    label=n.label,
                    shape=n.shape,
                    class_name=node_classes.get(n.id, n.class_name)
                )
                for n in nodes
            ]
    
    return MermaidBlock(
        source=source,
        diagram_type=diagram_type,
        nodes=nodes,
        edges=edges,
    )


def _parse_flowchart(lines: list[str]) -> tuple[list[MermaidNode], list[MermaidEdge], dict[str, str]]:
    """Parse flowchart TB/LR syntax."""
    nodes: list[MermaidNode] = []
    edges: list[MermaidEdge] = []
    node_classes: dict[str, str] = {}
    seen_node_ids: set[str] = set()
    
    for line in lines:
        # Skip directive lines
        if line.startswith(("flowchart", "subgraph", "end", "classDef", "linkStyle", "class")):
            # Handle class assignment: class A,B,C className
            if line.startswith("class "):
                parts = line[6:].split()
                if len(parts) >= 2:
                    node_ids = parts[0].split(",")
                    class_name = parts[1]
                    for nid in node_ids:
                        node_classes[nid.strip()] = class_name
            continue
        
        # Node definition: A[Label] or A(Label) or A{Label}
        node_match = re.match(r'^([A-Za-z0-9_]+)([\[\(\{])([^\]\)\}]+)([\]\)\}])(:::(\w+))?', line)
        if node_match:
            node_id = node_match.group(1)
            open_bracket = node_match.group(2)
            label = node_match.group(3)
            class_name = node_match.group(6) if node_match.group(5) else None
            
            shape = _bracket_to_shape(open_bracket)
            if node_id not in seen_node_ids:
                nodes.append(MermaidNode(
                    id=node_id,
                    label=label,
                    shape=shape,
                    class_name=class_name
                ))
                seen_node_ids.add(node_id)
            continue
        
        # Edge: A --> B or A -->|label| B or A -.->|label| B
        edge_match = re.match(
            r'^([A-Za-z0-9_]+)\s*(-->|-.->|===>|\-\.\->)\s*(?:\|([^\|]+)\|)?\s*([A-Za-z0-9_]+)',
            line
        )
        if edge_match:
            source_id = edge_match.group(1)
            arrow = edge_match.group(2)
            label = edge_match.group(3)
            target_id = edge_match.group(4)
            
            style = "solid"
            if "-.->" in arrow or ".-." in arrow:
                style = "dashed"
            
            edges.append(MermaidEdge(
                source=source_id,
                target=target_id,
                label=label,
                style=style
            ))
            continue
    
    return nodes, edges, node_classes


def _parse_sequence(lines: list[str]) -> tuple[list[MermaidNode], list[MermaidEdge]]:
    """Parse sequenceDiagram syntax."""
    nodes: list[MermaidNode] = []
    edges: list[MermaidEdge] = []
    seen_participants: set[str] = set()
    
    for line in lines:
        # participant Actor as Label
        participant_match = re.match(r'^participant\s+(\w+)(?:\s+as\s+(.+))?', line)
        if participant_match:
            node_id = participant_match.group(1)
            label = participant_match.group(2) or node_id
            if node_id not in seen_participants:
                nodes.append(MermaidNode(
                    id=node_id,
                    label=label,
                    shape="rectangle",
                    class_name=None
                ))
                seen_participants.add(node_id)
            continue
        
        # actor A as Label
        actor_match = re.match(r'^actor\s+(\w+)(?:\s+as\s+(.+))?', line)
        if actor_match:
            node_id = actor_match.group(1)
            label = actor_match.group(2) or node_id
            if node_id not in seen_participants:
                nodes.append(MermaidNode(
                    id=node_id,
                    label=label,
                    shape="actor",
                    class_name=None
                ))
                seen_participants.add(node_id)
            continue
        
        # A->>B: message or A-->>B: message
        message_match = re.match(r'^(\w+)\s*(->>|-->>|->>>\+|-->>-)\s*(\w+)\s*:\s*(.+)', line)
        if message_match:
            source_id = message_match.group(1)
            arrow = message_match.group(2)
            target_id = message_match.group(3)
            label = message_match.group(4)
            
            # Add participants if not seen
            for pid in (source_id, target_id):
                if pid not in seen_participants:
                    nodes.append(MermaidNode(
                        id=pid,
                        label=pid,
                        shape="rectangle",
                        class_name=None
                    ))
                    seen_participants.add(pid)
            
            style = "solid" if "->>" in arrow else "dashed"
            edges.append(MermaidEdge(
                source=source_id,
                target=target_id,
                label=label,
                style=style
            ))
            continue
    
    return nodes, edges


def _bracket_to_shape(bracket: str) -> str:
    """Convert Mermaid bracket notation to shape name."""
    mapping = {
        "[": "rectangle",
        "(": "rounded",
        "{": "diamond",
        "((": "circle",
        "([": "stadium",
        "[[": "subroutine",
        "[(": "cylinder",
        "{{": "hexagon",
    }
    return mapping.get(bracket, "rectangle")
