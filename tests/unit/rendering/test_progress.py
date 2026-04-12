"""Test progress reporting."""
from io import StringIO

from rich.console import Console

from uipath_claude.rendering.progress import ProgressReporter


def make_test_console() -> tuple[Console, StringIO]:
    """Create a console that captures output for testing."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)
    return console, output


class TestProgressReporter:
    """Test ProgressReporter class."""

    def test_init_default_console(self):
        """Test initialization with default console."""
        reporter = ProgressReporter()
        assert reporter.console is not None

    def test_init_custom_console(self):
        """Test initialization with custom console."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)
        assert reporter.console is console

    def test_success_message(self):
        """Test success message prints checkmark."""
        console, output = make_test_console()
        reporter = ProgressReporter(console=console)

        reporter.success("Operation completed")

        result = output.getvalue()
        assert "Operation completed" in result
        assert "\u2713" in result  # checkmark

    def test_error_message(self):
        """Test error message prints X."""
        console, output = make_test_console()
        reporter = ProgressReporter(console=console)

        reporter.error("Something failed")

        result = output.getvalue()
        assert "Something failed" in result
        assert "\u2717" in result  # X mark

    def test_warning_message(self):
        """Test warning message prints warning sign."""
        console, output = make_test_console()
        reporter = ProgressReporter(console=console)

        reporter.warning("Be careful")

        result = output.getvalue()
        assert "Be careful" in result
        assert "\u26a0" in result  # warning sign

    def test_info_message(self):
        """Test info message prints arrow."""
        console, output = make_test_console()
        reporter = ProgressReporter(console=console)

        reporter.info("Some information")

        result = output.getvalue()
        assert "Some information" in result
        assert "\u2192" in result  # arrow

    def test_file_written_message(self):
        """Test file written notification."""
        console, output = make_test_console()
        reporter = ProgressReporter(console=console)

        reporter.file_written("src/main.py")

        result = output.getvalue()
        assert "src/main.py" in result
        assert "\u2713" in result  # checkmark

    def test_analyzing_returns_status(self):
        """Test analyzing returns a Status object."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        status = reporter.analyzing()
        assert status is not None

    def test_selecting_skills_returns_status(self):
        """Test selecting_skills returns a Status object."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        status = reporter.selecting_skills()
        assert status is not None

    def test_generating_returns_status(self):
        """Test generating returns a Status object."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        status = reporter.generating()
        assert status is not None

    def test_generating_with_custom_artifact(self):
        """Test generating with custom artifact type."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        status = reporter.generating(artifact_type="project")
        assert status is not None

    def test_validating_returns_status(self):
        """Test validating returns a Status object."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        status = reporter.validating()
        assert status is not None

    def test_status_context_manager(self):
        """Test status context manager works."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        with reporter.status("Processing...") as status:
            assert status is not None

    def test_status_context_manager_custom_spinner(self):
        """Test status context manager with custom spinner."""
        console, _ = make_test_console()
        reporter = ProgressReporter(console=console)

        with reporter.status("Loading...", spinner="line") as status:
            assert status is not None
