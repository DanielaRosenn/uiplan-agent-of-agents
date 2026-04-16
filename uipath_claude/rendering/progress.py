"""Progress reporting for terminal output."""
import os
import time
from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.status import Status
from rich.text import Text

_TOOL_OUTPUT_BODY_MAX = 12000
_FINAL_RESPONSE_PREVIEW_MAX = 120


class ProgressReporter:
    """Progress reporter with spinner status and colored messages."""

    def __init__(self, console: Console | None = None):
        """
        Initialize progress reporter.

        Args:
            console: Rich console instance, creates new one if not provided
        """
        self.console = console or Console()

    @contextmanager
    def status(self, message: str, spinner: str = "dots") -> Generator[Status, None, None]:
        """
        Context manager for spinner status.

        Args:
            message: Status message to display
            spinner: Spinner style name

        Yields:
            Status object for updating message
        """
        with self.console.status(message, spinner=spinner) as status:
            yield status

    def analyzing(self) -> Status:
        """
        Return status for analyzing request.

        Returns:
            Status object with cyan analyzing message
        """
        return self.console.status("[cyan]Analyzing request...[/cyan]", spinner="dots")

    def selecting_skills(self) -> Status:
        """
        Return status for skill selection.

        Returns:
            Status object with cyan selecting message
        """
        return self.console.status("[cyan]Selecting skills...[/cyan]", spinner="dots")

    def generating(self, artifact_type: str = "workflow") -> Status:
        """
        Return status for generation.

        Args:
            artifact_type: Type of artifact being generated

        Returns:
            Status object with yellow generating message
        """
        return self.console.status(
            f"[yellow]Generating {artifact_type}...[/yellow]", spinner="dots"
        )

    def validating(self) -> Status:
        """
        Return status for validation.

        Returns:
            Status object with blue validating message
        """
        return self.console.status("[blue]Validating project...[/blue]", spinner="dots")

    def success(self, message: str) -> None:
        """
        Print success message with a green ASCII marker.

        Args:
            message: Success message to display
        """
        self.console.print(f"[green]+[/green] {message}")

    def error(self, message: str) -> None:
        """
        Print error message with a red ASCII marker.

        Args:
            message: Error message to display
        """
        self.console.print(f"[red]x[/red] {message}")

    def warning(self, message: str) -> None:
        """
        Print warning message with a yellow ASCII marker.

        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]![/yellow] {message}")

    def info(self, message: str) -> None:
        """
        Print info message.

        Args:
            message: Info message to display
        """
        self.console.print(f"[dim]->[/dim] {message}")

    def file_written(self, path: str) -> None:
        """
        Print file written notification.

        Args:
            path: Path of the file that was written
        """
        self.console.print(f"  [green]+[/green] {path}")


class AgenticProgressReporter:
    """Progress reporter for agentic execution with human-readable debug output."""

    def __init__(self, console: Console | None = None):
        """
        Initialize agentic progress reporter.

        Args:
            console: Rich console instance, creates new one if not provided
        """
        self.console = console or Console()
        self.verbose = os.environ.get("UIPATH_DEBUG_VERBOSE", "1").lower() in (
            "1",
            "true",
            "yes",
        )
        self.raw = os.environ.get("UIPATH_DEBUG_RAW", "0").lower() in ("1", "true", "yes")
        self.full_tool_output = os.environ.get(
            "UIPATH_AGENTIC_FULL_TOOL_OUTPUT", "0"
        ).lower() in ("1", "true", "yes")
        self.last_heartbeat_time = 0.0
        self.heartbeat_interval = 5.0  # Show heartbeat every 5 seconds

    def should_show_full_tool_body(self, success: bool) -> bool:
        """Whether to print the full tool result body after the one-line summary."""
        if not success:
            return True
        if self.verbose or self.raw:
            return True
        return self.full_tool_output

    def session_banner(self, artifact_root: str | None) -> None:
        """Print resolved session artifact directory once per agentic run."""
        if artifact_root:
            self.console.print(
                "[dim]Artifact root (this chat session):[/dim] "
                f"[cyan]{artifact_root}[/cyan]"
            )
            self.console.print()

    def skills_in_context(self, names: list[str], primary_skill: str) -> None:
        """Print selected skills once per agentic run (when names non-empty)."""
        cleaned = [str(n).strip() for n in names if str(n).strip()]
        if not cleaned:
            return

        # Structured marker for evaluation parser
        for skill_name in cleaned:
            self.console.print(f"[dim][SKILL: {skill_name}][/dim]")

        line = ", ".join(cleaned)
        extra = ""
        ps = str(primary_skill).strip() if primary_skill else ""
        if ps and ps != cleaned[0]:
            extra = f" — primary: {ps}"
        self.console.print(f"[dim]Skills in context:[/dim] [cyan]{line}[/cyan]{extra}")
        self.console.print()

    def iteration_start(self, n: int, max_iter: int) -> None:
        """
        Show iteration header with progress bar.

        Args:
            n: Current iteration number
            max_iter: Maximum iterations
        """
        bar_width = 20
        safe_max = max(1, max_iter)
        ratio = min(max(n, 0), safe_max) / safe_max
        filled = int(ratio * bar_width)
        filled = min(filled, bar_width - 1)
        remainder = bar_width - filled - 1
        track = "=" * filled + ">" + "\u00b7" * remainder

        self.console.print()
        self.console.print(f"[cyan]Step {n}/{safe_max}[/cyan] [{track}]")

    def thinking(self) -> None:
        """Show that the agent is thinking/planning."""
        self.console.print("  [dim]Thinking...[/dim]")
        self._maybe_show_heartbeat()
    
    def _maybe_show_heartbeat(self) -> None:
        """Show a heartbeat message if enough time has passed."""
        current_time = time.time()
        if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
            self.last_heartbeat_time = current_time
            self.console.print("  [dim]  (still working...)[/dim]")
    
    def heartbeat(self, message: str = "Processing...") -> None:
        """Show a heartbeat message to indicate ongoing work.
        
        Args:
            message: Custom message to display
        """
        self.console.print(f"  [dim]  {message}[/dim]")

    def no_tools_called(self, has_response: bool) -> None:
        """Show when LLM responded without calling tools."""
        if has_response:
            self.console.print("  [yellow]-> Responding (no tools used)[/yellow]")
        else:
            self.console.print("  [yellow]-> No action taken[/yellow]")

    def model_finished_without_tools(
        self,
        *,
        iteration: int,
        had_tool_calls_before: bool,
        final_text: str,
    ) -> None:
        """Report a model turn that returned no tool calls (done or first-turn idle).

        First iteration with no prior tools keeps legacy ``no_tools_called`` copy.
        Later turns (or after tools ran) print a short finishing line and optional preview.
        """
        if iteration == 1 and not had_tool_calls_before:
            self.no_tools_called(bool(final_text.strip()))
            return
        self.console.print(
            "  [dim]Finishing (no more tool calls this turn).[/dim]"
        )
        stripped = final_text.strip()
        if stripped:
            one_line = " ".join(stripped.split())
            preview = one_line[:_FINAL_RESPONSE_PREVIEW_MAX]
            if len(one_line) > _FINAL_RESPONSE_PREVIEW_MAX:
                preview += "…"
            self.console.print(f"  [dim]Preview: {preview}[/dim]")

    def tool_call(self, name: str, args: dict) -> None:
        """
        Show tool being called with icon.

        Args:
            name: Tool name
            args: Tool arguments
        """
        # Structured marker for evaluation parser (must be on its own line)
        self.console.print(f"[dim][TOOL_CALL: {name}][/dim]")

        # Map tool names to human-readable descriptions
        tool_descriptions = {
            "ensure_project_structure": "Creating project structure",
            "write_file": "Writing file",
            "read_file": "Reading file",
            "validate_file": "Validating file",
            "install_package": "Installing NuGet package",
            "find_activity_info": "Looking up activity info",
            "query_uipath_docs": "Searching UiPath docs",
            "validate_and_fix_loop": "Validating and fixing",
            "list_files": "Listing files",
            "run_workflow": "Running workflow",
            "deploy_to_orchestrator": "Deploying to Orchestrator",
            "write_documentation": "Writing documentation",
            "read_doc_template": "Reading doc template",
            "read_documentation": "Reading documentation",
            "list_documentation": "Listing documentation",
        }
        
        description = tool_descriptions.get(name, name)
        self.console.print(f"  [cyan]->[/cyan] {description}")
        
        # Show key arguments (always show something useful)
        if "file_path" in args:
            self.console.print(f"     [dim]File: {args['file_path']}[/dim]")
        elif "package_id" in args:
            self.console.print(f"     [dim]Package: {args['package_id']}[/dim]")
        elif "query" in args:
            query = args["query"]
            if len(query) > 60:
                query = query[:60] + "..."
            self.console.print(f"     [dim]Query: {query}[/dim]")
        elif "project_name" in args:
            self.console.print(f"     [dim]Project: {args['project_name']}[/dim]")
        
        # Show full args in verbose mode
        if self.verbose or self.raw:
            import json
            args_str = json.dumps(args, indent=2)
            if not self.verbose and len(args_str) > 300:
                args_str = args_str[:300] + "..."
            self.console.print(f"     [dim]{args_str}[/dim]")

    def tool_result(
        self,
        name: str,
        success: bool,
        result: str,
        *,
        show_full_body: bool = False,
    ) -> None:
        """
        Show result with status icon.

        Args:
            name: Tool name
            success: Whether tool succeeded
            result: Tool result message
            show_full_body: When True, print truncated full body after the summary line
        """
        if success:
            icon = "[green]+[/green]"
        else:
            icon = "[red]x[/red]"

        # Extract key info from result
        summary = self._summarize_result(name, result)
        self.console.print(f"     {icon} {summary}")

        if show_full_body and result.strip():
            body = result.strip()
            if len(body) > _TOOL_OUTPUT_BODY_MAX:
                body = body[:_TOOL_OUTPUT_BODY_MAX] + "\n\n… (truncated for console; full text is in tool messages)"
            self.console.print(
                Panel(
                    body,
                    title=f"[dim]Full output: {name}[/dim]",
                    border_style="dim",
                )
            )

    def _summarize_result(self, tool_name: str, result: str) -> str:
        """Create a human-readable summary of a tool result."""
        result_lower = result.lower()
        
        # Check for success patterns
        if "successfully" in result_lower:
            if "wrote" in result_lower or "created" in result_lower:
                return "File created"
            if "installed" in result_lower:
                return "Package installed"
            if "validated" in result_lower:
                return "Validation passed"
            return "Success"
        
        # Check for errors
        if "error" in result_lower or "failed" in result_lower:
            # Extract first line of error
            lines = result.strip().split("\n")
            first_line = lines[0][:80]
            if len(lines[0]) > 80:
                first_line += "..."
            return first_line
        
        # For validation results, show error count
        if "errors:" in result_lower:
            import re
            match = re.search(r"(\d+)\s*error", result_lower)
            if match:
                count = int(match.group(1))
                if count == 0:
                    return "No errors"
                return f"{count} error(s) found"
        
        # Default: show truncated result
        if not self.verbose:
            lines = result.strip().split("\n")
            if len(lines) > 1:
                return f"{lines[0][:60]}... ({len(lines)} lines)"
            if len(result) > 80:
                return result[:80] + "..."
        return result

    def complete(
        self,
        files_written: list[str],
        iterations: int,
        *,
        tool_success_count: int = 0,
        tool_failure_count: int = 0,
        artifact_root: str | None = None,
    ) -> None:
        """Show completion summary (loop finished, not necessarily all tools ok)."""
        self.console.print()
        self.console.print(
            f"[dim]Agent finished after {iterations} iteration(s)[/dim] "
            f"[dim](LLM rounds; not the same as 'all steps succeeded')[/dim]"
        )
        if tool_success_count or tool_failure_count:
            err_part = ""
            if tool_failure_count:
                err_part = f", [yellow]{tool_failure_count} reported errors[/yellow]"
            self.console.print(
                f"[dim]Tool calls this run:[/dim] [green]{tool_success_count} ok[/green]{err_part}"
            )
        if tool_failure_count:
            self.console.print(
                "[yellow]![/yellow] "
                f"{tool_failure_count} tool call(s) reported errors (see lines above). "
                "Failed tools always show full output above; set UIPATH_DEBUG_VERBOSE=0 "
                "or UIPATH_AGENTIC_FULL_TOOL_OUTPUT=0 for quieter successful-tool logs."
            )
        if artifact_root and not files_written:
            self.console.print(f"[dim]Artifact root:[/dim] [cyan]{artifact_root}[/cyan]")
        if files_written:
            self.console.print("[green]Files recorded as written:[/green]")
            for f in files_written:
                self.console.print(f"  [green]+[/green] {f}")
        self.console.print()

    def error(self, message: str) -> None:
        """Show error message."""
        self.console.print()
        self.console.print(f"[red]Error: {message}[/red]")
        self.console.print()

    def validation_status(self, errors: int, warnings: int, files: int = 1) -> None:
        """
        Show validation summary box.

        Args:
            errors: Number of errors
            warnings: Number of warnings
            files: Number of files validated
        """
        if errors > 0:
            style = "red"
            icon = "x"
        elif warnings > 0:
            style = "yellow"
            icon = "!"
        else:
            style = "green"
            icon = "+"
        
        self.console.print(f"  [{style}][{icon}][/{style}] Validation: {errors} error(s), {warnings} warning(s)")

    def doc_phase_start(self, doc_type: str, agent: str) -> None:
        """
        Show documentation phase starting.
        
        Args:
            doc_type: Type of document (pdd, sdd, add, tdd)
            agent: Agent type (ba or sa)
        """
        import sys
        agent_label = "Business Analyst" if agent == "ba" else "Solution Architect"
        # Structured marker for evaluation parser
        self.console.print(f"[dim][DOC_PHASE: {doc_type.upper()}][/dim]")
        self.console.print(f"[cyan]Creating {doc_type.upper()}[/cyan] using {agent_label} agent")
        self.console.print()
        sys.stdout.flush()

    def doc_created(self, doc_type: str, path: str) -> None:
        """
        Show documentation created successfully.
        
        Args:
            doc_type: Type of document (pdd, sdd, add, tdd)
            path: Path where document was saved
        """
        import sys
        # Structured marker for evaluation parser
        self.console.print(f"[dim][DOC_CREATED: {doc_type.upper()}][/dim]")
        self.console.print(f"[green]+[/green] {doc_type.upper()} created: {path}")
        sys.stdout.flush()

    def doc_skipped(self, doc_type: str, reason: str) -> None:
        """
        Show documentation skipped.
        
        Args:
            doc_type: Type of document
            reason: Why it was skipped
        """
        self.console.print(f"[yellow]![/yellow] {doc_type.upper()} skipped: {reason}")

    def doc_need_detected(self, level: str, docs: list[str]) -> None:
        """
        Show detected documentation needs.
        
        Args:
            level: Documentation need level (none, optional, recommended, required)
            docs: List of recommended document types
        """
        if level == "none":
            return
        
        level_colors = {
            "optional": "dim",
            "recommended": "yellow",
            "required": "cyan bold",
        }
        color = level_colors.get(level, "dim")
        
        if docs:
            docs_str = ", ".join(d.upper() for d in docs)
            self.console.print(f"[{color}]Documentation {level}:[/{color}] {docs_str}")
        else:
            self.console.print(f"[{color}]Documentation {level}[/{color}]")
