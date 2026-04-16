"""
Track UiPath Studio processes opened during testing to close only specific instances
"""
import json
import psutil
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime


class ProcessTracker:
    """Track processes opened during test session"""
    
    def __init__(self, tracking_file: Optional[Path] = None):
        """
        Initialize process tracker.
        
        Args:
            tracking_file: Path to JSON file for storing tracked PIDs
        """
        if tracking_file is None:
            tracking_file = Path.home() / ".uipath-claude" / "tracked_processes.json"
        
        self.tracking_file = Path(tracking_file)
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.tracked_pids: Set[int] = set()
        self.load()
    
    def load(self):
        """Load tracked PIDs from file"""
        if self.tracking_file.exists():
            try:
                data = json.loads(self.tracking_file.read_text())
                self.tracked_pids = set(data.get("pids", []))
                # Clean up PIDs that no longer exist
                self.tracked_pids = {
                    pid for pid in self.tracked_pids 
                    if psutil.pid_exists(pid)
                }
            except Exception:
                self.tracked_pids = set()
    
    def save(self):
        """Save tracked PIDs to file"""
        data = {
            "pids": list(self.tracked_pids),
            "last_updated": datetime.now().isoformat()
        }
        self.tracking_file.write_text(json.dumps(data, indent=2))
    
    def snapshot_before_test(self) -> Set[int]:
        """
        Take a snapshot of currently running UiPath processes before starting test.
        
        Returns:
            Set of PIDs that were already running
        """
        existing_pids = set()
        
        process_names = [
            "UiPath.Studio.exe",
            "UiStudio.exe", 
            "UiPath.Executor.exe",
            "robot.executor.exe"
        ]
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] in process_names:
                    existing_pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return existing_pids
    
    def track_new_processes(self, before_pids: Set[int]):
        """
        Identify and track new processes that started after test began.
        
        Args:
            before_pids: Set of PIDs that existed before test started
        """
        current_pids = self.snapshot_before_test()
        new_pids = current_pids - before_pids
        
        self.tracked_pids.update(new_pids)
        self.save()
        
        return new_pids
    
    def close_tracked_processes(self, force: bool = False) -> dict:
        """
        Close only the processes that were tracked during this session.
        
        Args:
            force: If True, force kill. If False, try graceful close first.
        
        Returns:
            dict with closed PIDs and any errors
        """
        closed = []
        errors = []
        
        for pid in list(self.tracked_pids):
            try:
                if not psutil.pid_exists(pid):
                    self.tracked_pids.remove(pid)
                    continue
                
                proc = psutil.Process(pid)
                proc_name = proc.name()
                
                if force:
                    proc.kill()
                else:
                    # Try graceful termination first
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except psutil.TimeoutExpired:
                        # Force kill if graceful doesn't work
                        proc.kill()
                
                closed.append({"pid": pid, "name": proc_name})
                self.tracked_pids.remove(pid)
                
            except psutil.NoSuchProcess:
                self.tracked_pids.remove(pid)
            except psutil.AccessDenied as e:
                errors.append({"pid": pid, "error": f"Access denied: {e}"})
            except Exception as e:
                errors.append({"pid": pid, "error": str(e)})
        
        self.save()
        
        return {
            "closed": closed,
            "errors": errors,
            "remaining": list(self.tracked_pids)
        }
    
    def get_tracked_count(self) -> int:
        """Get count of currently tracked processes"""
        # Clean up non-existent PIDs
        self.tracked_pids = {
            pid for pid in self.tracked_pids 
            if psutil.pid_exists(pid)
        }
        self.save()
        return len(self.tracked_pids)
    
    def clear_tracking(self):
        """Clear all tracked processes (use after manual cleanup)"""
        self.tracked_pids.clear()
        self.save()


# Global tracker instance
_tracker = None


def get_tracker() -> ProcessTracker:
    """Get global process tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = ProcessTracker()
    return _tracker


def start_tracking_test():
    """
    Call this before starting a test to snapshot existing processes.
    
    Returns:
        Snapshot of pre-existing PIDs
    """
    tracker = get_tracker()
    return tracker.snapshot_before_test()


def finish_tracking_test(before_pids: Set[int]):
    """
    Call this after test completes to track new processes.
    
    Args:
        before_pids: Result from start_tracking_test()
    
    Returns:
        Set of newly tracked PIDs
    """
    tracker = get_tracker()
    return tracker.track_new_processes(before_pids)


def close_test_processes(force: bool = False) -> dict:
    """
    Close only processes that were opened during tracked tests.
    
    Args:
        force: If True, force kill immediately
    
    Returns:
        dict with results
    """
    tracker = get_tracker()
    return tracker.close_tracked_processes(force=force)


def get_tracked_process_count() -> int:
    """Get count of tracked processes"""
    tracker = get_tracker()
    return tracker.get_tracked_count()


def clear_all_tracking():
    """Clear all process tracking"""
    tracker = get_tracker()
    tracker.clear_tracking()


UIPATH_AUTOMATION_PROCESS_NAMES = frozenset(
    (
        "UiPath.Studio.exe",
        "UiStudio.exe",
        "UiPath.Executor.exe",
        "robot.executor.exe",
    )
)


def snapshot_uipath_automation_pids() -> set[int]:
    """Return PIDs of UiPath Studio / Executor processes (for parent-side cleanup)."""
    pids: set[int] = set()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name")
            if name in UIPATH_AUTOMATION_PROCESS_NAMES:
                pids.add(int(proc.info["pid"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, KeyError):
            pass
    return pids


def close_uipath_processes_opened_since(
    before_pids: set[int], *, force: bool = False
) -> dict:
    """
    Terminate UiPath Studio/Executor processes that are running now but were not
    in ``before_pids``.

    Use from a **parent** test harness after each subprocess CLI run. Subprocess
    ``kill()`` on timeout may skip the CLI ``finally`` block, so this avoids
    orphaned Studio instances piling up.
    """
    after = snapshot_uipath_automation_pids()
    new_pids = after - set(before_pids)
    closed: list[dict] = []
    errors: list[dict] = []

    for pid in list(new_pids):
        try:
            if not psutil.pid_exists(pid):
                continue
            proc = psutil.Process(pid)
            proc_name = proc.name()
            if proc_name not in UIPATH_AUTOMATION_PROCESS_NAMES:
                continue
            if force:
                proc.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
            closed.append({"pid": pid, "name": proc_name})
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied as e:
            errors.append({"pid": pid, "error": f"Access denied: {e}"})
        except Exception as e:
            errors.append({"pid": pid, "error": str(e)})

    return {"closed": closed, "errors": errors}
