"""Central configuration defaults for uipath-claude."""
from __future__ import annotations

from uipath_claude.llm.router import (  # noqa: F401
    DEFAULT_HEAVY_MODEL,
    DEFAULT_LIGHT_MODEL,
    ModelTier,
    heavy_model,
    light_model,
    model_for,
    model_for_task,
)


def __getattr__(name: str) -> str:
    """Lazy attr so ``DEFAULT_BEDROCK_MODEL`` always reflects current env.

    Kept for back-compat with legacy importers
    (``from uipath_claude.config import DEFAULT_BEDROCK_MODEL``).
    """
    if name == "DEFAULT_BEDROCK_MODEL":
        return heavy_model()
    raise AttributeError(name)
