"""Test tool orchestration."""
from uipath_claude.query.orchestration import ToolOrchestrator


def test_tool_orchestrator_creation():
    """Test creating tool orchestrator."""
    orchestrator = ToolOrchestrator(tools=[])
    assert orchestrator.tools == []


def test_tool_orchestrator_add_tool():
    """Test adding tools."""
    orchestrator = ToolOrchestrator(tools=[])
    
    def test_tool():
        return "test"
    
    orchestrator.add_tool(test_tool)
    assert len(orchestrator.tools) == 1
