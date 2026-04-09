"""Integration tests for the chat flow."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from langchain_core.messages import AIMessage, HumanMessage


class TestChatFlowIntegration:
    """Integration tests for the full chat flow."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response."""
        return AIMessage(content="I can help you with UiPath automation.")

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample UiPath project."""
        project_json = tmp_path / "project.json"
        project_json.write_text('''{
            "name": "IntegrationTestProject",
            "projectId": "test-123",
            "description": "Test project",
            "main": "Main.xaml",
            "dependencies": {},
            "schemaVersion": "4.0"
        }''')
        (tmp_path / "Main.xaml").write_text("<Activity />")
        return tmp_path

    def test_project_detection_in_chat(self, sample_project):
        """Chat detects UiPath project context."""
        from agent.context.project_detector import detect_uipath_project

        context = detect_uipath_project(sample_project)

        assert context is not None
        assert context.name == "IntegrationTestProject"
        assert "Main.xaml" in context.workflows

    def test_slash_command_execution(self):
        """Slash commands execute correctly."""
        from cli.commands import parse_slash_command, execute_command

        parsed = parse_slash_command("/help")
        assert parsed is not None

        result = execute_command(parsed["command"], parsed["args"], {})
        assert "help" in result.lower()
        assert "status" in result.lower()

    def test_memory_loading(self, tmp_path):
        """Memory loads from global and project directories."""
        from agent.memory.loader import load_memory

        global_dir = tmp_path / "global"
        global_dir.mkdir()
        (global_dir / "memory.md").write_text("# Global\nGlobal context.")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        uipath_dir = project_dir / ".uipath-claude"
        uipath_dir.mkdir()
        (uipath_dir / "memory.md").write_text("# Project\nProject context.")

        memory = load_memory(global_dir=global_dir, project_dir=project_dir)

        assert "Global context" in memory.content
        assert "Project context" in memory.content

    def test_message_rendering(self):
        """Messages render correctly for terminal output."""
        from agent.rendering.message_renderer import render_message

        message = AIMessage(content="Hello, I can help with UiPath.")
        result = render_message(message)

        assert result == "Hello, I can help with UiPath."

    def test_hooks_fire_on_events(self):
        """Hooks fire correctly on events."""
        from agent.hooks.manager import HooksManager
        from agent.hooks.config import HookConfig, HookEvent

        manager = HooksManager()
        manager.register(HookConfig(
            event=HookEvent.SESSION_START,
            command="echo 'started'",
        ))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="started", stderr="")
            results = manager.fire(HookEvent.SESSION_START, {})

            assert len(results) == 1
            assert results[0]["success"]

    @pytest.mark.asyncio
    async def test_conversation_engine_loop(self):
        """Conversation engine handles tool loop correctly."""
        from agent.conversation_engine import ConversationEngine

        engine = ConversationEngine()

        mock_response = AIMessage(content="I'll help you create a workflow.")

        with patch.object(engine, '_invoke_model', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response

            result = await engine.run_turn([HumanMessage(content="Create a workflow")])

            assert result.content == "I'll help you create a workflow."
            assert mock_invoke.call_count == 1


class TestComponentIntegration:
    """Tests for component interactions."""

    def test_project_context_with_multiple_workflows(self, tmp_path):
        """Project detection finds all workflows."""
        from agent.context.project_detector import detect_uipath_project

        project_json = tmp_path / "project.json"
        project_json.write_text('{"name": "MultiWorkflow", "main": "Main.xaml"}')

        (tmp_path / "Main.xaml").write_text("<Activity />")
        (tmp_path / "Helper.xaml").write_text("<Activity />")

        subdir = tmp_path / "Workflows"
        subdir.mkdir()
        (subdir / "Process.xaml").write_text("<Activity />")

        context = detect_uipath_project(tmp_path)

        assert context is not None
        assert len(context.workflows) == 3
        assert "Main.xaml" in context.workflows
        assert "Helper.xaml" in context.workflows

    def test_memory_precedence(self, tmp_path):
        """Project memory appears after global memory."""
        from agent.memory.loader import load_memory

        global_dir = tmp_path / "global"
        global_dir.mkdir()
        (global_dir / "memory.md").write_text("GLOBAL_MARKER")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        uipath_dir = project_dir / ".uipath-claude"
        uipath_dir.mkdir()
        (uipath_dir / "memory.md").write_text("PROJECT_MARKER")

        memory = load_memory(global_dir=global_dir, project_dir=project_dir)

        global_pos = memory.content.find("GLOBAL_MARKER")
        project_pos = memory.content.find("PROJECT_MARKER")

        assert global_pos < project_pos, "Global memory should appear before project memory"

    def test_slash_command_with_args(self):
        """Slash commands parse arguments correctly."""
        from cli.commands import parse_slash_command

        parsed = parse_slash_command("/status verbose")

        assert parsed is not None
        assert parsed["command"] == "status"
        assert parsed["args"] == "verbose"

    def test_unknown_slash_command(self):
        """Unknown slash commands return helpful error."""
        from cli.commands import execute_command

        result = execute_command("nonexistent", "", {})

        assert "Unknown command" in result
        assert "/help" in result

    def test_hooks_pattern_matching(self):
        """Hooks match file patterns correctly."""
        from agent.hooks.manager import HooksManager
        from agent.hooks.config import HookConfig, HookEvent

        manager = HooksManager()
        manager.register(HookConfig(
            event=HookEvent.FILE_CHANGED,
            command="echo 'xaml changed'",
            pattern="*.xaml",
        ))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            results = manager.fire(HookEvent.FILE_CHANGED, {"file": "Main.xaml"})
            assert len(results) == 1

            results = manager.fire(HookEvent.FILE_CHANGED, {"file": "config.json"})
            assert len(results) == 0

    def test_message_rendering_with_content_blocks(self):
        """Message renderer handles content blocks."""
        from agent.rendering.message_renderer import render_content_blocks

        blocks = [
            {"type": "text", "text": "Starting analysis..."},
            {"type": "tool_use", "name": "read_file"},
            {"type": "text", "text": "Analysis complete."},
        ]

        result = render_content_blocks(blocks)

        assert "Starting analysis" in result
        assert "read_file" in result
        assert "Analysis complete" in result


class TestEndToEndScenarios:
    """End-to-end integration scenarios."""

    @pytest.mark.asyncio
    async def test_conversation_with_no_tools(self):
        """Conversation without tools returns direct response."""
        from agent.conversation_engine import ConversationEngine

        engine = ConversationEngine(tools=[])

        mock_response = AIMessage(content="Hello! How can I help?")

        with patch.object(engine, '_invoke_model', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response

            result = await engine.run_turn([HumanMessage(content="Hi")])

            assert result.content == "Hello! How can I help?"

    def test_full_project_workflow(self, tmp_path):
        """Full workflow: detect project, load memory, execute command."""
        from agent.context.project_detector import detect_uipath_project
        from agent.memory.loader import load_memory
        from cli.commands import parse_slash_command, execute_command

        project_json = tmp_path / "project.json"
        project_json.write_text('{"name": "E2EProject", "main": "Main.xaml"}')
        (tmp_path / "Main.xaml").write_text("<Activity />")

        uipath_dir = tmp_path / ".uipath-claude"
        uipath_dir.mkdir()
        (uipath_dir / "memory.md").write_text("Project-specific instructions.")

        context = detect_uipath_project(tmp_path)
        assert context is not None
        assert context.name == "E2EProject"

        memory = load_memory(project_dir=tmp_path)
        assert "Project-specific instructions" in memory.content

        parsed = parse_slash_command("/status")
        assert parsed is not None
        result = execute_command(parsed["command"], parsed["args"], {})
        assert result is not None
