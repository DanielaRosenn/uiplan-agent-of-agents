"""Test base tool classes."""
from uipath_claude.tools.base import BaseTool


def test_base_tool_creation():
    """Test creating a base tool."""
    class TestTool(BaseTool):
        name = "test_tool"
        description = "A test tool"
        
        def _run(self, **kwargs):
            return "test result"
    
    tool = TestTool()
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    result = tool._run()
    assert result == "test result"
