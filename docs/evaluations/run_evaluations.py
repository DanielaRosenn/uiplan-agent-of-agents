#!/usr/bin/env python3
"""
Two-Stage Evaluation Runner for UiPath Claude CLI

Runs test cases from test_cases.json and evaluates:
1. Technical: Tool calls, artifacts, error handling
2. Conceptual: Response quality against expected patterns
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Max chars of stdout/stderr stored per test (avoid huge JSON files)
_MAX_RAW_CHARS = 120_000

# Ensure repo root on path when running as `python docs/evaluations/run_evaluations.py`
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from uipath_claude.utils.process_tracker import (
    close_uipath_processes_opened_since,
    snapshot_uipath_automation_pids,
)


def _drain_text_lines(pipe: Any, acc: list[str]) -> None:
    """Read text pipe line-by-line until EOF (used so timeouts still keep partial output)."""
    try:
        if pipe is None:
            return
        while True:
            line = pipe.readline()
            if line == "":
                break
            acc.append(line)
    except Exception:
        pass


def _child_chat_argv() -> list[str]:
    """Run chat in the same interpreter with ``-u`` so stdout is not pipe-blocked."""
    return [
        sys.executable,
        "-u",
        "-c",
        "import sys; sys.argv = ['uipath-claude', 'chat', '--no-banner', '--track-processes']; "
        "from uipath_claude.cli.app import app; app()",
    ]


# Per-category timeout defaults (seconds)
# BUILD tests involve planning + multi-step execution with LLM calls
# QA/ERROR tests are simpler direct execution without planning
CATEGORY_TIMEOUTS = {
    'Workflow Building': 300,       # 5 min - planning + execution
    'Workflow Modification': 300,   # 5 min - planning + execution
    'Modification': 300,            # 5 min (alias)
    'Build and Deploy': 420,        # 7 min - planning + build + deploy
    'Build+Deploy': 420,            # 7 min (alias)
    'Question': 180,                # planner + tools often exceed 60s
    'Error Handling': 90,           # 1.5 min - error detection
    'Code Generation': 240,         # 4 min - planning + code gen
    'Clarification': 60,            # 1 min - simple prompts
    'Deployment': 180,              # 3 min
    'Authentication': 120,        # planning-heavy auth flows
    'Complex Scenario': 300,        # 5 min
    'Full Project': 300,            # 5 min
    'Validation': 180,            # Excel/build paths need write_file time
    'Edge Case': 90,                # 1.5 min
    'Integration': 180,             # 3 min
    'Performance': 120,             # 2 min
    'Learning': 120,              # memory preference can trigger broad exploration
    'Library': 60,                # doc library tools + short answers
    'Subagent Routing': 180,    # persona/subagent routing eval cases
    'Full project E2E': 600,        # 10 min (deferred long tests)
}
DEFAULT_TIMEOUT = 180  # 3 min fallback


class CLITestRunner:
    """Runs CLI tests and captures output."""
    
    def __init__(self, project_dir: str | None = None, timeout: int | None = None):
        repo_root = Path(__file__).resolve().parent.parent.parent
        self.project_dir = project_dir or str(repo_root / "tests" / "fixtures" / "sample_project")
        self.base_timeout = timeout  # None means use category defaults
    
    def get_timeout(self, category: str) -> int:
        """Get timeout for a test category."""
        if self.base_timeout is not None:
            return self.base_timeout
        return CATEGORY_TIMEOUTS.get(category, DEFAULT_TIMEOUT)

    def run_test(self, user_input: str, category: str = '') -> dict:
        """Run a single test and capture output.

        Always closes UiPath Studio/Executor spawned during this run (parent-side).
        Subprocess ``kill()`` on timeout can skip the CLI ``finally`` cleanup.
        """
        timeout = self.get_timeout(category)
        env = os.environ.copy()
        env['UIPATH_SKIP_AUTH_CHECK'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        if 'UIPATH_PLANNER_MAX_ITERATIONS' not in env:
            env['UIPATH_PLANNER_MAX_ITERATIONS'] = '10'

        if category.strip() == 'Library':
            import tempfile

            env['UIPATH_CLAUDE_LIBRARY_PROPOSALS'] = tempfile.mkdtemp(
                prefix='uipath-lib-eval-proposals-'
            )

        # Empty input still sends exit so the session closes
        full_input = f"{user_input}\nexit\n" if user_input else "exit\n"

        before_pids = snapshot_uipath_automation_pids()
        process = None
        try:
            process = subprocess.Popen(
                _child_chat_argv(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.project_dir,
                env=env,
            )

            # Threaded drain: on Windows, communicate(timeout=) does not attach partial streams
            # to TimeoutExpired; draining lines preserves markers for triage when we kill the CLI.
            out_acc: list[str] = []
            err_acc: list[str] = []
            assert process.stdout is not None and process.stderr is not None
            t_out = threading.Thread(
                target=_drain_text_lines, args=(process.stdout, out_acc), daemon=True
            )
            t_err = threading.Thread(
                target=_drain_text_lines, args=(process.stderr, err_acc), daemon=True
            )
            t_out.start()
            t_err.start()

            assert process.stdin is not None
            process.stdin.write(full_input)
            process.stdin.close()

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait(timeout=60)
                except Exception:
                    pass
                t_out.join(timeout=60)
                t_err.join(timeout=60)
                stdout = "".join(out_acc)
                stderr = "".join(err_acc)
                tail = f"Timeout after {timeout}s"
                return {
                    'success': False,
                    'error': 'timeout',
                    'stdout': stdout,
                    'stderr': f"{stderr}\n{tail}" if stderr.strip() else tail,
                    'exit_code': -1,
                    'crashed': 'traceback' in stderr.lower(),
                }

            t_out.join(timeout=120)
            t_err.join(timeout=120)
            stdout = "".join(out_acc)
            stderr = "".join(err_acc)
            return {
                'success': True,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': process.returncode,
                'crashed': 'traceback' in (stderr or "").lower(),
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'crashed': True,
            }
        finally:
            cleanup = close_uipath_processes_opened_since(before_pids, force=False)
            if cleanup.get("closed"):
                # Brief log to stderr so batch runs show progress even with buffered stdout
                names = ", ".join(f"{c['name']}:{c['pid']}" for c in cleanup["closed"])
                print(f"  [cleanup] Closed {len(cleanup['closed'])} UiPath process(es): {names}", flush=True)


class OutputParser:
    """Parse CLI output for evaluation."""
    
    @staticmethod
    def extract_tool_calls(stdout: str) -> list[str]:
        """Extract tool calls from output using structured markers."""
        tools = []
        # Primary: structured [TOOL_CALL: name] markers
        for match in re.finditer(r'\[TOOL_CALL:\s*(\w+)\]', stdout):
            tools.append(match.group(1))
        # Fallback: old -> pattern (for backwards compatibility)
        if not tools:
            for match in re.finditer(r'->\s+(\w+)', stdout):
                tool = match.group(1)
                # Filter out non-tool names
                if tool.lower() not in ('skills', 'searching', 'creating', 'validating', 'writing', 'responding'):
                    tools.append(tool)
        return tools
    
    @staticmethod
    def extract_skills(stdout: str) -> list[str]:
        """Extract invoked skills from output using structured markers."""
        skills = []
        for match in re.finditer(r'\[SKILL:\s*([^\]]+)\]', stdout):
            skills.append(match.group(1).strip())
        return skills

    @staticmethod
    def extract_document_types(stdout: str) -> list[str]:
        """Extract selected document-output types from structured markers."""
        document_types: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r'\[DOCUMENT_TYPE:\s*([^\]]+)\]', stdout):
            doc_type = match.group(1).strip().upper()
            if doc_type in {"ADD", "TDD"} and doc_type not in seen:
                seen.add(doc_type)
                document_types.append(doc_type)
        return document_types
    
    @staticmethod
    def extract_files_written(stdout: str) -> list[str]:
        """Extract file paths mentioned as written/created (best-effort from CLI text)."""
        files: list[str] = []
        # Pattern 1: "Successfully wrote N bytes to /path/to/file.xaml"
        for match in re.finditer(
            r"Successfully wrote \d+ bytes to\s+([^\s\r\n]+\.(?:xaml|json|cs|md))",
            stdout,
            re.IGNORECASE,
        ):
            files.append(match.group(1))
        # Pattern 2: "Wrote: path" or "Created path.xaml at ..."
        for match in re.finditer(
            r"(?:Wrote|Created|Saved):\s*\n?\s*([^\s\r\n]+\.(?:xaml|json|cs|md))",
            stdout,
            re.IGNORECASE,
        ):
            files.append(match.group(1))
        for match in re.finditer(
            r"(?:Created|Wrote)\s+([^\s\r\n]+\.(?:xaml|json|cs|md))\s+at",
            stdout,
            re.IGNORECASE,
        ):
            files.append(match.group(1))
        # Pattern 3: "File created" marker in tool output followed by path
        for match in re.finditer(
            r"\+\s+File created.*?([^\s\r\n\\]+\.xaml)",
            stdout,
            re.IGNORECASE | re.DOTALL,
        ):
            files.append(match.group(1))
        # Pattern 4: "Files recorded as written:" summary (Rich; ANSI stripped elsewhere)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", stdout)
        block_start = plain.find("Files recorded as written:")
        if block_start >= 0:
            for line in plain[block_start:].splitlines()[1:40]:
                line = line.strip()
                m = re.search(
                    r"(?:^\+|\+\s+)([^\s|]+\.(?:xaml|json|cs|md))\s*$",
                    line,
                    re.IGNORECASE,
                )
                if m:
                    files.append(m.group(1))
        # Pattern 5: write_file arg echo "File: path.xaml"
        for match in re.finditer(
            r"File:\s+([^\s\r\n|]+\.(?:xaml|json|cs|md))",
            plain,
            re.IGNORECASE,
        ):
            files.append(match.group(1))
        # De-duplicate preserving order
        seen: set[str] = set()
        out: list[str] = []
        for f in files:
            # Extract just the filename from full paths
            filename = f.split('\\')[-1].split('/')[-1]
            if filename not in seen:
                seen.add(filename)
                out.append(filename)
        return out
    
    @staticmethod
    def extract_errors(stdout: str, stderr: str) -> list[str]:
        """Extract errors from output."""
        errors = []
        for match in re.finditer(r'[x✗]\s+Error:?\s*(.+)', stdout):
            errors.append(match.group(1))
        for match in re.finditer(r'Error:\s*(.+)', stderr):
            errors.append(match.group(1))
        return errors
    
    @staticmethod
    def _strip_session_tail(text: str) -> str:
        """Remove trailing user exit lines and parent-side Studio cleanup."""
        t = text.strip()
        t = re.sub(r"(?s)\n*You:\s*(?:exit|Goodbye)!\s*", "\n", t, flags=re.IGNORECASE)
        t = re.sub(
            r"(?s)\n*Closed\s+\d+\s+test\s+Studio\s+process(?:es)?\s*$",
            "",
            t,
            flags=re.IGNORECASE,
        )
        return t.strip()

    @staticmethod
    def _implementation_plan_fallback(clean: str) -> str:
        """Rich panel: boxed 'Implementation Plan' content."""
        if "Implementation Plan" not in clean:
            return ""
        start = -1
        for m in re.finditer(r"┌[^\n]*Implementation Plan[^\n]*", clean):
            start = m.start()
        if start < 0:
            start = clean.find("┌")
        if start < 0:
            return ""
        end = clean.find("└", start)
        if end < 0:
            return ""
        block = clean[start : end + 1]
        lines = []
        for line in block.splitlines():
            if "│" in line:
                # Drop border glyphs; keep inner text
                inner = line.split("│", 1)[-1].rstrip("│").strip()
                if inner:
                    lines.append(inner)
        return "\n".join(lines).strip()

    @staticmethod
    def _last_preview_after_executing(clean: str) -> str:
        """Last 'Preview:' line after [EXECUTING] (model text without tool markers)."""
        exec_idx = clean.rfind("[EXECUTING]")
        chunk = clean[exec_idx:] if exec_idx >= 0 else clean
        previews: list[str] = []
        for line in chunk.splitlines():
            m = re.search(r"Preview:\s*(.+)$", line, re.IGNORECASE)
            if m:
                previews.append(m.group(1).strip())
        return previews[-1] if previews else ""

    @staticmethod
    def extract_assistant_response(stdout: str) -> str:
        """Extract the assistant's final response (after tool execution)."""
        # Remove ANSI codes
        clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
        clean = OutputParser._strip_session_tail(clean)

        def _finalize(candidate: str) -> str:
            c = OutputParser._strip_session_tail(candidate)
            if len(c) < 12:
                return ""
            low = c.lower()
            if low in ("goodbye!", "exit"):
                return ""
            return c

        # Try to find text after "Agent finished" markers (final response after tools)
        markers = [
            "Agent finished after",
            "Tool calls this run:",
            "Files recorded as written:",
        ]
        last_pos = 0
        for marker in markers:
            pos = clean.rfind(marker)
            if pos > last_pos:
                last_pos = pos

        response = ""
        if last_pos > 0:
            # Get text after the marker section
            after = clean[last_pos:]
            # Skip past the summary lines (usually ends with empty line)
            lines = after.split('\n')
            # Find the start of actual response content (skip summary lines)
            response_start = 0
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 0:
                    # Found end of summary section
                    response_start = i + 1
                    break
                if i > 10:
                    # Safety: don't skip too many lines
                    break

            if response_start > 0 and response_start < len(lines):
                response = '\n'.join(lines[response_start:]).strip()

        if not _finalize(response):
            # Fallback: find text after "Assistant:" label
            parts = clean.split('Assistant:')
            if len(parts) > 1:
                response = parts[-1].strip()

        out = _finalize(response)
        if out:
            return out

        # Prefer full plan text over short final Preview (Preview often omits Excel/retry details).
        plan = OutputParser._implementation_plan_fallback(clean)
        out = _finalize(plan)
        if out:
            return out

        preview = OutputParser._last_preview_after_executing(clean)
        out = _finalize(preview)
        if out:
            return out

        return clean
    
    @staticmethod
    def detect_mode(stdout: str) -> str:
        """Detect which mode the agent used from structured markers."""
        has_planning = '[PLANNING]' in stdout
        has_executing = '[EXECUTING]' in stdout
        
        if has_planning and has_executing:
            return 'planning_then_execution'
        if has_planning:
            return 'planning'
        if has_executing:
            return 'execution'

        # Direct Q&A (non-planning chat turn); must win over scripted "Goodbye" at end of harness input
        if '[ANSWERING]' in stdout:
            return 'direct_response'

        # Fallback heuristics
        if '?' in stdout and 'clarif' in stdout.lower():
            return 'clarification'
        # User exited with no agent phase (banner only, or exit before planner runs)
        if not has_planning and not has_executing and re.search(
            r"You:\s*(exit|Goodbye)!", stdout, re.IGNORECASE
        ):
            return 'exit'
        return 'direct_response'


class TechnicalEvaluator:
    """Evaluate technical aspects of CLI output."""

    def __init__(self, parsed_output: dict, expected: dict):
        self.output = parsed_output
        self.expected = expected
        self.results: dict[str, list[str]] = {
            'passed': [],
            'failed': [],
            'routing_failed': [],
            'warnings': [],
        }

    def evaluate(self) -> dict:
        """Run all technical evaluations."""
        self._check_crash()
        self._check_mode()
        self._check_skills_routing()
        self._check_document_type_routing()
        self._check_tool_calls()
        self._check_no_file_creation()
        self._check_artifacts_forbidden()
        self._check_safety_phrases()
        self._check_artifacts()
        self._check_errors()

        blocking = self._routing_failure_blocking()
        routing_failed = self.results['routing_failed']
        execution_failed = self.results['failed']
        routing_ok = len(routing_failed) == 0
        execution_ok = len(execution_failed) == 0
        passed = execution_ok and (routing_ok or not blocking)

        return {
            'passed': passed,
            'routing_passed': routing_ok,
            'routing_failure_is_blocking': blocking,
            'checks_passed': len(self.results['passed']),
            'checks_failed': len(self.results['failed']),
            'routing_checks_failed': len(routing_failed),
            'warnings': len(self.results['warnings']),
            'details': self.results,
        }

    def _routing_failure_blocking(self) -> bool:
        explicit = self.expected.get('routing_failure_is_blocking')
        if explicit is not None:
            return bool(explicit)
        return bool(
            self.expected.get('skills_required')
            or self.expected.get('skills_forbidden')
            or self.expected.get('document_type_required')
            or self.expected.get('document_type_forbidden')
            or self.expected.get('no_file_creation')
            or self.expected.get('artifacts_forbidden')
            or self.expected.get('safety_forbidden_phrases')
        )

    @staticmethod
    def _skill_present(required: str, skills: list[str]) -> bool:
        req = required.strip().lower()
        if not req:
            return False
        for line in skills:
            sl = line.strip().lower()
            if req == sl or req in sl or sl.endswith(req):
                return True
        return False

    def _check_skills_routing(self) -> None:
        skills = self.output.get('skills') or []
        req = self.expected.get('skills_required')
        required = req if isinstance(req, list) else []
        for name in required:
            if self._skill_present(name, skills):
                self.results['passed'].append(f'Skill marker present: {name}')
            else:
                self.results['routing_failed'].append(
                    f'Missing required skill marker: {name} (have {skills!r})'
                )

        forb = self.expected.get('skills_forbidden')
        forbidden = forb if isinstance(forb, list) else []
        for name in forbidden:
            if self._skill_present(name, skills):
                self.results['routing_failed'].append(
                    f'Forbidden skill marker present: {name}'
                )
            else:
                self.results['passed'].append(f'Forbidden skill absent (ok): {name}')

        rexp = self.expected.get('routing_expected')
        if isinstance(rexp, str) and rexp.strip():
            self.results['passed'].append(f'routing_expected (informational): {rexp}')

    def _check_document_type_routing(self) -> None:
        doc_types = [
            str(value).strip().upper()
            for value in (self.output.get('document_types') or [])
            if str(value).strip()
        ]

        required = self.expected.get('document_type_required')
        if isinstance(required, str) and required.strip():
            req = required.strip().upper()
            if req in doc_types:
                self.results['passed'].append(f'Document type present: {req}')
            else:
                self.results['routing_failed'].append(
                    f'Missing document type: {req} (have {doc_types!r})'
                )

        forbidden = self.expected.get('document_type_forbidden')
        values = forbidden if isinstance(forbidden, list) else []
        for raw in values:
            value = str(raw or '').strip().upper()
            if not value:
                continue
            if value in doc_types:
                self.results['routing_failed'].append(
                    f'Forbidden document type present: {value}'
                )
            else:
                self.results['passed'].append(f'Forbidden document type absent (ok): {value}')

    def _check_no_file_creation(self) -> None:
        if not self.expected.get('no_file_creation'):
            return
        files = self.output.get('files_written') or []
        if files:
            self.results['routing_failed'].append(
                f'no_file_creation: files were written {files!r}'
            )
        else:
            self.results['passed'].append('no_file_creation: no files written')

    def _check_artifacts_forbidden(self) -> None:
        raw = self.expected.get('artifacts_forbidden')
        patterns = raw if isinstance(raw, list) else []
        if not patterns:
            return
        files = self.output.get('files_written') or []
        hay = ' '.join(files).lower()
        for pat in patterns:
            p = (pat or '').lower().strip()
            if not p:
                continue
            if p.startswith('*'):
                suf = p[1:]
                hit = any(f.lower().endswith(suf) for f in files)
            else:
                hit = p in hay or any(p in f.lower() for f in files)
            if hit:
                self.results['routing_failed'].append(
                    f'Forbidden artifact matched pattern {pat!r}'
                )
            else:
                self.results['passed'].append(f'Forbidden artifact absent (ok): {pat}')

    def _check_safety_phrases(self) -> None:
        raw = self.expected.get('safety_forbidden_phrases')
        phrases = raw if isinstance(raw, list) else []
        if not phrases:
            return
        combined = self.output.get('safety_text') or self.output.get('combined_text') or ''
        for phrase in phrases:
            p = (phrase or '').lower().strip()
            if not p:
                continue
            if p in combined:
                self.results['routing_failed'].append(
                    f'Safety: forbidden phrase present: {phrase!r}'
                )
            else:
                self.results['passed'].append(f'Safety: phrase absent (ok): {phrase}')
    
    def _check_crash(self):
        if self.expected.get('crash_not_allowed', True):
            if self.output.get('crashed'):
                self.results['failed'].append('CRASH: Unhandled exception detected')
            else:
                self.results['passed'].append('No crash')
    
    def _check_mode(self):
        expected_mode = self.expected.get('mode')
        if expected_mode:
            actual_mode = self.output.get('mode')
            if self._mode_compatible(expected_mode, actual_mode):
                self.results['passed'].append(f'Mode: {actual_mode}')
            else:
                self.results['failed'].append(f'Mode: expected {expected_mode}, got {actual_mode}')

    @staticmethod
    def _mode_compatible(expected: str, actual: str) -> bool:
        """CLI often prints [PLANNING] then [EXECUTING]; tests may still say 'execution'."""
        if actual == expected:
            return True
        if expected == 'execution' and actual in (
            'planning_then_execution',
            'planning',
        ):
            return True
        if expected == 'planning_then_execution' and actual == 'planning':
            return True
        return False
    
    def _check_tool_calls(self):
        actual_tools = self.output.get('tool_calls', [])
        
        required = self.expected.get('tool_calls_required', [])
        for tool in required:
            if tool in actual_tools:
                self.results['passed'].append(f'Tool called: {tool}')
            else:
                self.results['failed'].append(f'Missing required tool: {tool}')

        raw_any = self.expected.get('tool_calls_required_any_of')
        any_of = raw_any if isinstance(raw_any, list) else []
        if any_of:
            if any(tool in actual_tools for tool in any_of):
                self.results['passed'].append(
                    f'Required tool group satisfied: one of {any_of!r}'
                )
            else:
                self.results['failed'].append(
                    f'Missing required tool (need any of): {any_of}'
                )

        optional = self.expected.get('tool_calls_optional', [])
        for tool in optional:
            if tool in actual_tools:
                self.results['passed'].append(f'Optional tool called: {tool}')
    
    def _check_artifacts(self):
        artifacts = self.expected.get('artifacts', {})
        files_written = self.output.get('files_written', [])
        
        expected_files = artifacts.get('files_created', [])
        for pattern in expected_files:
            if pattern.startswith('*'):
                # Glob pattern (e.g. *.xaml, *.md)
                ext = pattern[1:]
                if any(f.endswith(ext) for f in files_written):
                    self.results['passed'].append(f'File created: {pattern}')
                else:
                    self.results['failed'].append(f'Missing file: {pattern}')
            else:
                if any(
                    pattern == f
                    or f.endswith(pattern)
                    or pattern in f.replace('\\', '/')
                    for f in files_written
                ):
                    self.results['passed'].append(f'File created: {pattern}')
                else:
                    self.results['failed'].append(f'Missing file: {pattern}')
    
    def _check_errors(self):
        errors = self.output.get('errors', [])
        acceptable = self.expected.get('errors_acceptable', [])
        
        for error in errors:
            error_lower = error.lower()
            is_acceptable = any(acc.lower() in error_lower for acc in acceptable)
            if is_acceptable:
                self.results['passed'].append(f'Acceptable error: {error[:50]}')
            else:
                self.results['warnings'].append(f'Error: {error[:50]}')


class ConceptualEvaluator:
    """Evaluate conceptual aspects of response quality."""
    
    def __init__(self, response: str, expected: dict, extra_text: str = ""):
        self.response = response.lower()
        self.response_original = response
        self.extra_text = (extra_text or "").lower()
        self.expected = expected
        self.results = {'passed': [], 'failed': [], 'warnings': []}

    def _haystack(self) -> str:
        """Assistant text plus tool error lines (often contain 'not found', etc.)."""
        if not self.extra_text:
            return self.response
        return f"{self.response}\n{self.extra_text}"
    
    def evaluate(self) -> dict:
        """Run all conceptual evaluations."""
        self._check_must_contain_all()
        self._check_must_contain_any()
        self._check_must_not_contain()
        self._check_should_mention()
        
        return {
            'passed': len(self.results['failed']) == 0,
            'checks_passed': len(self.results['passed']),
            'checks_failed': len(self.results['failed']),
            'warnings': len(self.results['warnings']),
            'details': self.results,
            'response_preview': self.response_original[:500]
        }
    
    def _check_must_contain_all(self):
        phrases = self.expected.get('response_must_contain_all', [])
        hay = self._haystack()
        for phrase in phrases:
            if phrase.lower() in hay:
                self.results['passed'].append(f'Contains: {phrase}')
            else:
                self.results['failed'].append(f'Missing required: {phrase}')
    
    def _check_must_contain_any(self):
        phrases = self.expected.get('response_must_contain_any', [])
        if not phrases:
            return
        
        hay = self._haystack()
        found = [p for p in phrases if p.lower() in hay]
        if found:
            self.results['passed'].append(f'Contains one of: {found[0]}')
        else:
            self.results['failed'].append(f'Missing any of: {phrases}')
    
    def _check_must_not_contain(self):
        phrases = self.expected.get('response_must_not_contain', [])
        for phrase in phrases:
            if phrase.lower() in self.response:
                self.results['failed'].append(f'Should not contain: {phrase}')
            else:
                self.results['passed'].append(f'Does not contain: {phrase}')
    
    def _check_should_mention(self):
        phrases = self.expected.get('response_should_mention', [])
        hay = self._haystack()
        for phrase in phrases:
            if phrase.lower() in hay:
                self.results['passed'].append(f'Mentions: {phrase}')
            else:
                self.results['warnings'].append(f'Should mention: {phrase}')


def run_evaluation(test_case: dict, runner: CLITestRunner) -> dict:
    """Run a single test case evaluation."""
    test_id = test_case['test_id']
    user_input = test_case['input']
    expected = test_case['expected']
    category = test_case['category']
    preview = (user_input[:60] + "...") if len(user_input) > 60 else user_input or "(empty)"
    timeout = runner.get_timeout(category)
    
    print(f"\n{'='*60}")
    print(f"Running: {test_id} - {category}")
    print(f"Input: {preview}")
    print(f"Timeout: {timeout}s ({category})")
    print(f"{'='*60}")
    
    t0 = time.perf_counter()
    # Run CLI test
    cli_result = runner.run_test(user_input, category)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    
    # Parse output
    assistant_response = OutputParser.extract_assistant_response(cli_result['stdout'])
    parsed = {
        'stdout': cli_result['stdout'],
        'stderr': cli_result['stderr'],
        'crashed': cli_result.get('crashed', False),
        'tool_calls': OutputParser.extract_tool_calls(cli_result['stdout']),
        'skills': OutputParser.extract_skills(cli_result['stdout']),
        'document_types': OutputParser.extract_document_types(cli_result['stdout']),
        'files_written': OutputParser.extract_files_written(cli_result['stdout']),
        'errors': OutputParser.extract_errors(cli_result['stdout'], cli_result['stderr']),
        'mode': OutputParser.detect_mode(cli_result['stdout']),
        'response': assistant_response,
        'combined_text': (
            (cli_result.get('stdout') or '') + '\n' + (cli_result.get('stderr') or '')
        ).lower(),
        'safety_text': (
            (assistant_response or '') + '\n' + (cli_result.get('stderr') or '')
        ).lower(),
    }
    
    # Evaluate technical
    tech_eval = TechnicalEvaluator(parsed, expected.get('technical', {}))
    tech_result = tech_eval.evaluate()
    
    # Evaluate conceptual
    concept_extra = "\n".join(parsed.get("errors", [])[:40])
    concept_eval = ConceptualEvaluator(
        parsed["response"], expected.get("conceptual", {}), extra_text=concept_extra
    )
    concept_result = concept_eval.evaluate()
    
    out = cli_result.get('stdout') or ''
    err = cli_result.get('stderr') or ''
    result = {
        'test_id': test_id,
        'category': test_case['category'],
        'input': user_input,
        'duration_ms': duration_ms,
        'cli_success': cli_result.get('success', False),
        'cli_error': cli_result.get('error'),
        'exit_code': cli_result.get('exit_code'),
        'parsed': {
            'mode': parsed['mode'],
            'tool_calls': parsed['tool_calls'],
            'skills': parsed.get('skills', []),
            'document_types': parsed.get('document_types', []),
            'files_written': parsed['files_written'],
            'errors': parsed['errors'][:20],
            'assistant_response_preview': (parsed['response'] or '')[:2000],
        },
        'technical': tech_result,
        'conceptual': concept_result,
        'overall_passed': tech_result['passed'] and concept_result['passed'],
        'raw_output': {
            'stdout': out[:_MAX_RAW_CHARS],
            'stderr': err[: min(50_000, _MAX_RAW_CHARS)],
            'stdout_truncated': len(out) > _MAX_RAW_CHARS,
        },
    }
    
    # Print summary
    tech_status = 'PASS' if tech_result['passed'] else 'FAIL'
    concept_status = 'PASS' if concept_result['passed'] else 'FAIL'
    rf = tech_result.get('routing_checks_failed', 0)
    ef = tech_result.get('checks_failed', 0)
    print(
        f"Technical: {tech_status} "
        f"(exec_failed={ef}, routing_failed={rf}, "
        f"routing_blocking={tech_result.get('routing_failure_is_blocking')})"
    )
    print(f"Conceptual: {concept_status} ({concept_result['checks_passed']}/{concept_result['checks_passed'] + concept_result['checks_failed']})")
    
    return result


def _write_per_test(log_dir: Path, result: dict, test_case: dict) -> None:
    """Write one JSON file per test for triage."""
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'test_id': result['test_id'],
        'category': result['category'],
        'input': result['input'],
        'duration_ms': result.get('duration_ms'),
        'timestamp': datetime.now().isoformat(),
        'expected': test_case.get('expected'),
        'result': result,
    }
    out_path = log_dir / f"{result['test_id']}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Run CLI evaluations')
    parser.add_argument(
        '--test',
        action='append',
        dest='tests',
        metavar='TEST_ID',
        help='Run specific test(s) by ID (repeat flag for multiple)',
    )
    parser.add_argument('--category', help='Run tests in category')
    parser.add_argument('--output', help='Aggregate results JSON file')
    parser.add_argument(
        '--log-dir',
        default='',
        help='Directory for per-test JSON logs (default: docs/evaluations/results)',
    )
    parser.add_argument('--project-dir', help='UiPath project directory for tests')
    parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help=(
            'Override per-test CLI timeout in seconds (default: per CATEGORY_TIMEOUTS '
            'in this file, e.g. Workflow Building 300s, Question 180s, Deployment 180s)'
        ),
    )
    parser.add_argument(
        '--only-full-project-e2e',
        action='store_true',
        help='Run only tests with skip_in_default_batch=true (the four full-project E2E cases)',
    )
    parser.add_argument(
        '--include-full-project-e2e',
        action='store_true',
        help='Run the default batch plus deferred full-project E2E tests',
    )
    args = parser.parse_args()
    
    # Load test cases
    test_file = Path(__file__).parent / 'test_cases.json'
    with open(test_file, encoding='utf-8') as f:
        data = json.load(f)
    
    all_cases: list[dict] = data['test_cases']
    test_cases = list(all_cases)
    skipped_e2e = 0
    
    # Filter tests
    if args.tests:
        wanted = {x for x in args.tests if x}
        test_cases = [t for t in test_cases if t['test_id'] in wanted]
        missing = wanted - {t['test_id'] for t in test_cases}
        if missing:
            print(f"Unknown test id(s): {', '.join(sorted(missing))}", flush=True)
            return 1
    elif args.category:
        test_cases = [t for t in test_cases if t['category'] == args.category]
    elif args.only_full_project_e2e:
        test_cases = [t for t in test_cases if t.get('skip_in_default_batch')]
        if not test_cases:
            print("No tests marked skip_in_default_batch found")
            return 1
    elif args.include_full_project_e2e:
        test_cases = list(all_cases)
    else:
        deferred = [t for t in test_cases if t.get('skip_in_default_batch')]
        skipped_e2e = len(deferred)
        test_cases = [t for t in test_cases if not t.get('skip_in_default_batch')]
    
    if not test_cases:
        print("No matching test cases found")
        return 1
    
    print(f"Running {len(test_cases)} test(s)...", flush=True)
    if skipped_e2e and not args.tests and not args.category:
        print(
            f"  (Skipped {skipped_e2e} full-project E2E case(s); "
            "use --only-full-project-e2e or --include-full-project-e2e to run them.)",
            flush=True,
        )
    
    default_log = Path(__file__).resolve().parent / 'results'
    log_dir = Path(args.log_dir) if args.log_dir else default_log
    
    # Initialize runner
    runner = CLITestRunner(project_dir=args.project_dir, timeout=args.timeout)
    
    # Run evaluations
    results = []
    run_started = datetime.now().isoformat()
    for test_case in test_cases:
        result = run_evaluation(test_case, runner)
        results.append(result)
        _write_per_test(log_dir, result, test_case)
        print(f"  Logged: {log_dir / (result['test_id'] + '.json')}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r['overall_passed'])
    failed = len(results) - passed
    
    print(f"Total: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {passed/len(results)*100:.1f}%")
    
    if failed > 0:
        print(f"\nFailed tests:")
        for r in results:
            if not r['overall_passed']:
                print(f"  - {r['test_id']}: {r['category']}")
    
    # Always write aggregate summary next to per-test logs
    summary_path = log_dir / 'run_summary.json'
    summary = {
        'run_started': run_started,
        'run_finished': datetime.now().isoformat(),
        'project_dir': runner.project_dir,
        'timeout_mode': 'fixed' if args.timeout else 'per-category',
        'timeout_override': args.timeout,
        'category_timeouts': CATEGORY_TIMEOUTS if not args.timeout else None,
        'log_dir': str(log_dir.resolve()),
        'skipped_full_project_e2e': skipped_e2e,
        'only_full_project_e2e': bool(args.only_full_project_e2e),
        'include_full_project_e2e': bool(args.include_full_project_e2e),
        'total': len(results),
        'passed': passed,
        'failed': failed,
        'pass_rate_pct': round(passed / len(results) * 100, 2) if results else 0,
        'results': [
            {
                'test_id': r['test_id'],
                'category': r['category'],
                'overall_passed': r['overall_passed'],
                'duration_ms': r.get('duration_ms'),
                'technical_passed': r['technical']['passed'],
                'routing_passed': r['technical'].get('routing_passed'),
                'routing_checks_failed': r['technical'].get('routing_checks_failed'),
                'conceptual_passed': r['conceptual']['passed'],
            }
            for r in results
        ],
    }
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")

    # Optional full dump (large)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'timestamp': datetime.now().isoformat(),
                    'total': len(results),
                    'passed': passed,
                    'failed': failed,
                    'results': results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Full results saved to: {output_path}")

    # Markdown triage list for fixing later
    md_path = log_dir / 'TRIAGE.md'
    timeout_info = (
        f'Fixed: {args.timeout}s'
        if args.timeout
        else 'Per-category (see CATEGORY_TIMEOUTS in run_evaluations.py)'
    )
    lines = [
        '# Evaluation run triage',
        '',
        f'- Finished: {summary["run_finished"]}',
        f'- Total: {len(results)}, Passed: {passed}, Failed: {failed}',
        f'- Project dir: `{runner.project_dir}`',
        f'- Timeout: {timeout_info}',
        f'- Skipped full-project E2E (not in this run): {skipped_e2e}',
        '',
        '| Test ID | Category | Overall | Tech | Routing | Concept | ms | Log |',
        '|---------|----------|---------|------|---------|---------|-----|-----|',
    ]
    for r in results:
        tid = r['test_id']
        rp = r['technical'].get('routing_passed')
        routing_cell = 'PASS' if rp else 'FAIL'
        lines.append(
            f'| {tid} | {r["category"]} | '
            f'{"PASS" if r["overall_passed"] else "FAIL"} | '
            f'{"PASS" if r["technical"]["passed"] else "FAIL"} | '
            f'{routing_cell} | '
            f'{"PASS" if r["conceptual"]["passed"] else "FAIL"} | '
            f'{r.get("duration_ms", 0)} | [{tid}.json](./{tid}.json) |'
        )
    lines.extend(['', 'Fix expectations or product behavior per row; re-run when ready.'])
    md_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Triage list: {md_path}")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
