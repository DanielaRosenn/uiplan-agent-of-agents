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


class CLITestRunner:
    """Runs CLI tests and captures output."""
    
    def __init__(self, project_dir: str | None = None, timeout: int = 120):
        repo_root = Path(__file__).resolve().parent.parent.parent
        self.project_dir = project_dir or str(repo_root / "tests" / "fixtures" / "sample_project")
        self.timeout = timeout
    
    def run_test(self, user_input: str) -> dict:
        """Run a single test and capture output.

        Always closes UiPath Studio/Executor spawned during this run (parent-side).
        Subprocess ``kill()`` on timeout can skip the CLI ``finally`` cleanup.
        """
        env = os.environ.copy()
        env['UIPATH_SKIP_AUTH_CHECK'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'

        # Empty input still sends exit so the session closes
        full_input = f"{user_input}\nexit\n" if user_input else "exit\n"

        before_pids = snapshot_uipath_automation_pids()
        process = None
        try:
            process = subprocess.Popen(
                [
                    "uipath-claude",
                    "chat",
                    "--no-banner",
                    "--track-processes",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.project_dir,
                env=env,
            )

            stdout, stderr = process.communicate(
                input=full_input, timeout=self.timeout
            )

            return {
                'success': True,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': process.returncode,
                'crashed': 'traceback' in (stderr or "").lower(),
            }

        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except Exception:
                pass
            return {
                'success': False,
                'error': 'timeout',
                'stdout': '',
                'stderr': f'Timeout after {self.timeout}s',
                'exit_code': -1,
                'crashed': False,
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
    def extract_files_written(stdout: str) -> list[str]:
        """Extract file paths mentioned as written/created (best-effort from CLI text)."""
        files: list[str] = []
        # Panel lines: "Wrote: path" or "Created path.xaml at ..."
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
        # De-duplicate preserving order
        seen: set[str] = set()
        out: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                out.append(f)
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
    def extract_assistant_response(stdout: str) -> str:
        """Extract the assistant's response."""
        # Remove ANSI codes
        clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
        
        # Find assistant response
        parts = clean.split('Assistant:')
        if len(parts) > 1:
            response = parts[-1].strip()
            # Remove trailing prompt
            response = re.sub(r'\n*You:\s*exit\s*$', '', response)
            return response
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
        
        # Fallback heuristics
        if '?' in stdout and 'clarif' in stdout.lower():
            return 'clarification'
        return 'direct_response'


class TechnicalEvaluator:
    """Evaluate technical aspects of CLI output."""
    
    def __init__(self, parsed_output: dict, expected: dict):
        self.output = parsed_output
        self.expected = expected
        self.results = {'passed': [], 'failed': [], 'warnings': []}
    
    def evaluate(self) -> dict:
        """Run all technical evaluations."""
        self._check_crash()
        self._check_mode()
        self._check_tool_calls()
        self._check_artifacts()
        self._check_errors()
        
        return {
            'passed': len(self.results['failed']) == 0,
            'checks_passed': len(self.results['passed']),
            'checks_failed': len(self.results['failed']),
            'warnings': len(self.results['warnings']),
            'details': self.results
        }
    
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
            if actual_mode == expected_mode:
                self.results['passed'].append(f'Mode: {actual_mode}')
            else:
                self.results['failed'].append(f'Mode: expected {expected_mode}, got {actual_mode}')
    
    def _check_tool_calls(self):
        actual_tools = self.output.get('tool_calls', [])
        
        required = self.expected.get('tool_calls_required', [])
        for tool in required:
            if tool in actual_tools:
                self.results['passed'].append(f'Tool called: {tool}')
            else:
                self.results['failed'].append(f'Missing required tool: {tool}')
        
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
    
    def __init__(self, response: str, expected: dict):
        self.response = response.lower()
        self.response_original = response
        self.expected = expected
        self.results = {'passed': [], 'failed': [], 'warnings': []}
    
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
        for phrase in phrases:
            if phrase.lower() in self.response:
                self.results['passed'].append(f'Contains: {phrase}')
            else:
                self.results['failed'].append(f'Missing required: {phrase}')
    
    def _check_must_contain_any(self):
        phrases = self.expected.get('response_must_contain_any', [])
        if not phrases:
            return
        
        found = [p for p in phrases if p.lower() in self.response]
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
        for phrase in phrases:
            if phrase.lower() in self.response:
                self.results['passed'].append(f'Mentions: {phrase}')
            else:
                self.results['warnings'].append(f'Should mention: {phrase}')


def run_evaluation(test_case: dict, runner: CLITestRunner) -> dict:
    """Run a single test case evaluation."""
    test_id = test_case['test_id']
    user_input = test_case['input']
    expected = test_case['expected']
    preview = (user_input[:60] + "...") if len(user_input) > 60 else user_input or "(empty)"
    
    print(f"\n{'='*60}")
    print(f"Running: {test_id} - {test_case['category']}")
    print(f"Input: {preview}")
    print(f"{'='*60}")
    
    t0 = time.perf_counter()
    # Run CLI test
    cli_result = runner.run_test(user_input)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    
    # Parse output
    parsed = {
        'stdout': cli_result['stdout'],
        'stderr': cli_result['stderr'],
        'crashed': cli_result.get('crashed', False),
        'tool_calls': OutputParser.extract_tool_calls(cli_result['stdout']),
        'skills': OutputParser.extract_skills(cli_result['stdout']),
        'files_written': OutputParser.extract_files_written(cli_result['stdout']),
        'errors': OutputParser.extract_errors(cli_result['stdout'], cli_result['stderr']),
        'mode': OutputParser.detect_mode(cli_result['stdout']),
        'response': OutputParser.extract_assistant_response(cli_result['stdout'])
    }
    
    # Evaluate technical
    tech_eval = TechnicalEvaluator(parsed, expected.get('technical', {}))
    tech_result = tech_eval.evaluate()
    
    # Evaluate conceptual
    concept_eval = ConceptualEvaluator(parsed['response'], expected.get('conceptual', {}))
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
    print(f"Technical: {tech_status} ({tech_result['checks_passed']}/{tech_result['checks_passed'] + tech_result['checks_failed']})")
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
    parser.add_argument('--test', help='Run specific test by ID')
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
        default=120,
        help='Per-test CLI timeout in seconds (default: 120)',
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
    if args.test:
        test_cases = [t for t in test_cases if t['test_id'] == args.test]
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
    if skipped_e2e and not args.test and not args.category:
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
        'timeout_seconds': args.timeout,
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
    lines = [
        '# Evaluation run triage',
        '',
        f'- Finished: {summary["run_finished"]}',
        f'- Total: {len(results)}, Passed: {passed}, Failed: {failed}',
        f'- Project dir: `{runner.project_dir}`',
        f'- Timeout per test: {args.timeout}s',
        f'- Skipped full-project E2E (not in this run): {skipped_e2e}',
        '',
        '| Test ID | Category | Overall | Tech | Concept | ms | Log |',
        '|---------|----------|---------|------|---------|-----|-----|',
    ]
    for r in results:
        tid = r['test_id']
        lines.append(
            f'| {tid} | {r["category"]} | '
            f'{"PASS" if r["overall_passed"] else "FAIL"} | '
            f'{"PASS" if r["technical"]["passed"] else "FAIL"} | '
            f'{"PASS" if r["conceptual"]["passed"] else "FAIL"} | '
            f'{r.get("duration_ms", 0)} | [{tid}.json](./{tid}.json) |'
        )
    lines.extend(['', 'Fix expectations or product behavior per row; re-run when ready.'])
    md_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Triage list: {md_path}")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
