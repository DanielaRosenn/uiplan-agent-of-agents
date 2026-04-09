"""Environment information collection."""
import platform
import sys
from pathlib import Path


def get_environment_info() -> dict[str, str]:
    """
    Collect environment information.
    
    Returns:
        Dictionary with environment details
    """
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "platform_release": platform.release(),
        "cwd": str(Path.cwd()),
    }
