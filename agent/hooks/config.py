"""Hook configuration types."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HookEvent(Enum):
    """Supported hook events."""

    SESSION_START = "session_start"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    FILE_CHANGED = "file_changed"


@dataclass
class HookConfig:
    """Configuration for a single hook."""

    event: HookEvent
    command: str
    pattern: Optional[str] = None
    timeout: int = 30
