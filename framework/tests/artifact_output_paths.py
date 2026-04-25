"""Single canonical on-disk area for tests that materialize file trees (gitignored).

``generated/test-runs/pytest/`` is for automated pytest. Human/manual review runs
may use ``generated/test-runs/manual-review/<id>/`` (see manual review checklists).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# framework/tests/artifact_output_paths.py -> parents[0]=tests, [1]=framework, [2]=repo
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
PYTEST_FILE_TREE_ROOT: Path = REPO_ROOT / "generated" / "test-runs" / "pytest"


_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def ensure_subdir(relative: str) -> Path:
    """Create ``generated/test-runs/pytest/<relative>/`` and return it.

    *relative* must be a single safe path segment (no ``..``, no separators).
    """
    if not relative or relative.strip() != relative:
        raise ValueError("relative must be a non-empty trimmed string")
    if ".." in relative or os.path.sep in relative or (os.altsep and os.altsep in relative):
        raise ValueError("relative must not contain '..' or path separators")
    if not _SEGMENT.fullmatch(relative):
        raise ValueError("relative must be one alphanumeric segment with ._- only")
    p = PYTEST_FILE_TREE_ROOT / relative
    p.mkdir(parents=True, exist_ok=True)
    return p
