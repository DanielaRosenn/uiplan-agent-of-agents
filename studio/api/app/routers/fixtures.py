"""Export project graphs as TypeScript fixtures for the frontend demo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.explorer import _allowed_worktree_roots, _is_within, _repo_root, get_project_graph


router = APIRouter(prefix="/fixtures", tags=["fixtures"])


@router.post("/export-demo")
async def export_demo_fixture(
    source_path: str,
    output_name: str = "sample",
) -> dict[str, Any]:
    """Export a project graph as a TypeScript fixture for demo purposes.
    
    Args:
        source_path: Path to the project to export
        output_name: Name for the fixture file (default: "sample")
    
    Returns:
        Success message with the output path
    """
    # Validate source path
    candidate = Path(source_path)
    if not candidate.is_absolute():
        candidate = (_repo_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {source_path}")
    
    allowed = _allowed_worktree_roots()
    if not any(_is_within(candidate, root) for root in allowed):
        raise HTTPException(
            status_code=403,
            detail="Folder path is not in the allow-list",
        )
    
    # Get the project graph
    graph_response = await get_project_graph(str(candidate))
    
    if not graph_response or "nodes" not in graph_response:
        raise HTTPException(status_code=500, detail="Failed to generate project graph")
    
    # Generate TypeScript fixture
    ts_content = _generate_typescript_fixture(graph_response, output_name)
    
    # Write to fixtures directory
    fixtures_dir = _repo_root() / "studio" / "web" / "src" / "__fixtures__"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = fixtures_dir / f"{output_name}.ts"
    output_path.write_text(ts_content, encoding="utf-8")
    
    return {
        "success": True,
        "output_path": str(output_path),
        "nodes": len(graph_response.get("nodes", [])),
        "edges": len(graph_response.get("edges", [])),
        "project_type": graph_response.get("projectType", "unknown"),
    }


def _generate_typescript_fixture(graph: dict[str, Any], name: str) -> str:
    """Generate TypeScript code for a project graph fixture."""
    # Clean up the graph for export
    cleaned = {
        "projectType": graph.get("projectType", "unknown"),
        "meta": {
            "worktree_id": "demo",
            "branch": graph.get("meta", {}).get("branch", "main"),
            "revision": f"{name}-fixture",
            "indexed_at": "new Date().toISOString()",
            "project_type": graph.get("projectType", "unknown"),
        },
        "overview": graph.get("overview"),
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
        "errors": graph.get("errors", []),
    }
    
    # Convert to JSON with proper formatting
    json_str = json.dumps(cleaned, indent=2, ensure_ascii=False)
    
    # Replace the indexed_at placeholder with actual code
    json_str = json_str.replace('"new Date().toISOString()"', 'new Date().toISOString()')
    
    # Generate TypeScript
    ts_content = f'''import type {{ ProjectGraph }} from "../projectGraph/types";

/**
 * Exported project graph fixture: {name}
 * Generated from: {graph.get("meta", {}).get("worktree_id", "unknown")}
 * 
 * This fixture can be used as demo content in the UiPlan Studio.
 * To regenerate: POST /fixtures/export-demo with the source project path.
 */
export const {name}Graph: ProjectGraph = {json_str};
'''
    
    return ts_content


@router.get("/list")
async def list_fixtures() -> dict[str, Any]:
    """List available fixture files."""
    fixtures_dir = _repo_root() / "studio" / "web" / "src" / "__fixtures__"
    
    if not fixtures_dir.exists():
        return {"fixtures": []}
    
    fixtures = []
    for file in fixtures_dir.glob("*.ts"):
        if file.stem == "types":
            continue
        
        content = file.read_text(encoding="utf-8")
        
        # Try to extract basic info from the fixture
        info = {
            "name": file.stem,
            "path": str(file),
            "size": file.stat().st_size,
        }
        
        # Count nodes/edges if possible
        if "nodes:" in content:
            nodes_match = content.count('"id":')
            info["approx_nodes"] = nodes_match
        
        fixtures.append(info)
    
    return {"fixtures": fixtures}
