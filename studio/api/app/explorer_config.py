"""Loader for the per-project `.uiplan/explorer.yaml` config.

Every project that wants to be navigable by the UiPlan Studio Explorer drops
a `.uiplan/explorer.yaml` at its root. The file captures the parts a Business
Analyst cares about (name, owner, triggers, actors, KPIs) plus optional
indexer hints (which globs to scan per layer).

The schema is intentionally permissive — missing keys yield empty defaults
rather than errors, so a half-filled file still produces a useful overview
panel. Schema-shape errors raise `ExplorerConfigError` with a clear message.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIRNAME = ".uiplan"
CONFIG_FILENAME = "explorer.yaml"
ANNOTATIONS_FILENAME = "annotations.yaml"


class ExplorerConfigError(ValueError):
    """Raised when an explorer.yaml file is structurally invalid."""


@dataclass(frozen=True)
class TriggerSpec:
    kind: str
    description: str = ""


@dataclass(frozen=True)
class ActorSpec:
    name: str
    role: str = ""


@dataclass(frozen=True)
class KpiSpec:
    label: str
    value: str


@dataclass(frozen=True)
class HandoffSpec:
    """A single handoff in the AS-IS manual process."""
    from_actor: str
    to_actor: str
    channel: str = ""  # email | phone | excel | paper | meeting
    artifact: str = ""
    sla: str = ""
    pain: str = ""
    docs: str | None = None


@dataclass(frozen=True)
class AsIsSpec:
    """AS-IS manual process view configuration."""
    summary_from: str | None = None
    diagram_from: str | None = None
    actors_from: str | None = None  # e.g. "explorer.actors"
    swimlanes: tuple[str, ...] = ()
    handoffs: tuple[HandoffSpec, ...] = ()
    pain_points: str | None = None


@dataclass(frozen=True)
class ToBeSpec:
    """TO-BE automated solution view configuration."""
    architecture_from: tuple[str, ...] = ()
    runtime_sequence_from: str | None = None
    workflow_catalog_from: str | None = None
    integrations_from: str = "indexed"
    drill_docs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewsSpec:
    """Views configuration for AS-IS and TO-BE canvases."""
    docs_root: str = "docs/"
    as_is: AsIsSpec = field(default_factory=AsIsSpec)
    to_be: ToBeSpec = field(default_factory=ToBeSpec)


@dataclass(frozen=True)
class ProjectSpec:
    name: str = "(unnamed project)"
    type: str = "unknown"
    owner: str | None = None
    pdd: str | None = None


@dataclass(frozen=True)
class OverviewSpec:
    summary: str = ""
    stakeholders: tuple[str, ...] = ()
    triggers: tuple[TriggerSpec, ...] = ()
    actors: tuple[ActorSpec, ...] = ()
    kpis: tuple[KpiSpec, ...] = ()


# Sensible default scan globs per project type. Used when explorer.yaml
# omits the `indexing.scan` block. Conservative — better to under-scan than
# to lock the indexer up walking node_modules.
DEFAULT_SCAN_GLOBS: dict[str, dict[str, list[str]]] = {
    "rpa": {
        "rpa": ["**/*.xaml", "Main.xaml", "**/Project.json"],
        "test": ["**/Test_Framework/**/*.xaml"],
    },
    "coded-agent": {
        "agent": ["**/agent.py", "**/main.py", "agent/**/*.py"],
    },
    "langgraph": {
        "agent": ["**/agent.py", "**/graph.py", "**/main.py", "agent/**/*.py"],
    },
    "solution": {
        "ui":           ["apps/**/src/**/*.tsx", "apps/**/src/**/*.ts"],
        "api":          ["services/**/app/**/*.py", "backend/**/*.py"],
        "agent":        ["agent/**/*.py", "**/main.py"],
        "rpa":          ["**/*.xaml"],
        "maestro":      ["**/*.flow", "**/*.bpmn"],
        "app":          ["apps/**/app.config.json", "apps/**/action-schema.json"],
        "test":         ["tests/**/*.testset.json"],
    },
    "mixed": {
        "ui":     ["src/**/*.tsx", "src/**/*.ts"],
        "api":    ["backend/**/*.py", "services/**/*.py"],
        "agent":  ["agent/**/*.py"],
        "rpa":    ["**/*.xaml"],
        "test":   ["tests/**/*.py"],
    },
    "unknown": {
        "ui":    ["src/**/*.tsx", "src/**/*.ts"],
        "api":   ["**/*.py"],
        "rpa":   ["**/*.xaml"],
    },
}

DEFAULT_EXCLUDES: tuple[str, ...] = (
    # virtual envs / package caches (match anywhere in the tree, not just root)
    ".venv/**", "**/.venv/**", "venv/**", "**/venv/**",
    "**/site-packages/**",
    "node_modules/**", "**/node_modules/**",
    "**/__pycache__/**",
    "**/dist/**", "**/build/**",
    ".git/**", "**/.git/**",
    ".cursor/plans/**",
    ".worktrees/**", "**/.worktrees/**",
    "**/.uipath/**",
    # additional ecosystem caches
    "**/.next/**", "**/.turbo/**", "**/.cache/**",
    "**/coverage/**", "**/.pytest_cache/**", "**/.mypy_cache/**",
    "**/.tox/**", "**/.eggs/**", "**/*.egg-info/**",
)


@dataclass(frozen=True)
class IndexingSpec:
    """Globs the indexer scans per layer + globs to skip."""
    scan: dict[str, tuple[str, ...]] = field(default_factory=dict)
    exclude: tuple[str, ...] = field(default_factory=lambda: DEFAULT_EXCLUDES)
    max_files_per_layer: int = 200
    max_file_bytes: int = 256 * 1024


@dataclass(frozen=True)
class ExplorerConfig:
    project: ProjectSpec = field(default_factory=ProjectSpec)
    overview: OverviewSpec = field(default_factory=OverviewSpec)
    indexing: IndexingSpec = field(default_factory=IndexingSpec)
    views: ViewsSpec = field(default_factory=ViewsSpec)
    source_path: str | None = None  # absolute path the config was loaded from


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------


def find_config_path(start: Path) -> Path | None:
    """Walk upwards from `start` looking for `.uiplan/explorer.yaml`.

    Returns the absolute file path or None if no config exists in any ancestor.
    """
    current = start.resolve()
    while True:
        candidate = current / CONFIG_DIRNAME / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def load_config(project_root: Path) -> ExplorerConfig:
    """Load `.uiplan/explorer.yaml` from `project_root`. Returns defaults if absent."""
    candidate = project_root / CONFIG_DIRNAME / CONFIG_FILENAME
    if not candidate.is_file():
        # Best-effort default: detect project type from the directory.
        project_type = _detect_project_type(project_root)
        return ExplorerConfig(
            project=ProjectSpec(name=project_root.name or "(unnamed project)", type=project_type),
            indexing=IndexingSpec(scan=_default_scan_for(project_type)),
            source_path=None,
        )
    return load_config_file(candidate)


def load_config_file(path: Path) -> ExplorerConfig:
    """Load a specific explorer.yaml file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExplorerConfigError(f"{path}: invalid YAML — {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ExplorerConfigError(f"{path}: top-level YAML must be a mapping, got {type(raw).__name__}")
    return _from_mapping(raw, source_path=str(path))


# ---------------------------------------------------------------------------
# Mapping → dataclasses
# ---------------------------------------------------------------------------


def _from_mapping(raw: dict[str, Any], *, source_path: str | None) -> ExplorerConfig:
    project = _parse_project(raw.get("project") or {})
    overview = _parse_overview(raw.get("overview") or {})
    indexing = _parse_indexing(raw.get("indexing") or {}, project_type=project.type)
    views = _parse_views(raw.get("views") or {})
    return ExplorerConfig(
        project=project,
        overview=overview,
        indexing=indexing,
        views=views,
        source_path=source_path,
    )


def _parse_project(raw: Any) -> ProjectSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError("project: must be a mapping")
    return ProjectSpec(
        name=str(raw.get("name") or "(unnamed project)"),
        type=str(raw.get("type") or "unknown"),
        owner=_opt_str(raw.get("owner")),
        pdd=_opt_str(raw.get("pdd")),
    )


def _parse_overview(raw: Any) -> OverviewSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError("overview: must be a mapping")
    return OverviewSpec(
        summary=str(raw.get("summary") or ""),
        stakeholders=tuple(str(s) for s in raw.get("stakeholders") or () if s),
        triggers=tuple(_parse_trigger(t) for t in raw.get("triggers") or ()),
        actors=tuple(_parse_actor(a) for a in raw.get("actors") or ()),
        kpis=tuple(_parse_kpi(k) for k in raw.get("kpis") or ()),
    )


def _parse_trigger(raw: Any) -> TriggerSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError(f"triggers entry must be a mapping, got {type(raw).__name__}")
    if not raw.get("kind"):
        raise ExplorerConfigError("trigger: 'kind' is required")
    return TriggerSpec(kind=str(raw["kind"]), description=str(raw.get("description") or ""))


def _parse_actor(raw: Any) -> ActorSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError(f"actors entry must be a mapping, got {type(raw).__name__}")
    if not raw.get("name"):
        raise ExplorerConfigError("actor: 'name' is required")
    return ActorSpec(name=str(raw["name"]), role=str(raw.get("role") or ""))


def _parse_kpi(raw: Any) -> KpiSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError(f"kpis entry must be a mapping, got {type(raw).__name__}")
    if not raw.get("label") or raw.get("value") is None:
        raise ExplorerConfigError("kpi: 'label' and 'value' are required")
    return KpiSpec(label=str(raw["label"]), value=str(raw["value"]))


def _parse_indexing(raw: Any, *, project_type: str) -> IndexingSpec:
    if not isinstance(raw, dict):
        raise ExplorerConfigError("indexing: must be a mapping")
    scan_raw = raw.get("scan")
    if scan_raw is None:
        scan = _default_scan_for(project_type)
    else:
        if not isinstance(scan_raw, dict):
            raise ExplorerConfigError("indexing.scan: must be a mapping {layer: [globs]}")
        scan = {
            str(layer): tuple(str(g) for g in globs or ())
            for layer, globs in scan_raw.items()
        }
    exclude_raw = raw.get("exclude")
    if exclude_raw is None:
        exclude = DEFAULT_EXCLUDES
    else:
        if not isinstance(exclude_raw, list):
            raise ExplorerConfigError("indexing.exclude: must be a list of globs")
        exclude = tuple(str(g) for g in exclude_raw)
    return IndexingSpec(
        scan=scan,
        exclude=exclude,
        max_files_per_layer=int(raw.get("max_files_per_layer") or 200),
        max_file_bytes=int(raw.get("max_file_bytes") or 256 * 1024),
    )


def _parse_views(raw: Any) -> ViewsSpec:
    """Parse views configuration for AS-IS and TO-BE canvases."""
    if not isinstance(raw, dict):
        raise ExplorerConfigError("views: must be a mapping")
    
    docs_root = str(raw.get("docs_root") or "docs/")
    as_is = _parse_as_is(raw.get("as_is") or {})
    to_be = _parse_to_be(raw.get("to_be") or {})
    
    return ViewsSpec(docs_root=docs_root, as_is=as_is, to_be=to_be)


def _parse_as_is(raw: Any) -> AsIsSpec:
    """Parse AS-IS manual process configuration."""
    if not isinstance(raw, dict):
        raise ExplorerConfigError("views.as_is: must be a mapping")
    
    swimlanes = tuple(str(s) for s in raw.get("swimlanes") or ())
    handoffs_raw = raw.get("handoffs") or ()
    handoffs = tuple(_parse_handoff(h) for h in handoffs_raw)
    
    return AsIsSpec(
        summary_from=_opt_str(raw.get("summary_from")),
        diagram_from=_opt_str(raw.get("diagram_from")),
        actors_from=_opt_str(raw.get("actors_from")),
        swimlanes=swimlanes,
        handoffs=handoffs,
        pain_points=_opt_str(raw.get("pain_points")),
    )


def _parse_handoff(raw: Any) -> HandoffSpec:
    """Parse a single handoff specification."""
    if not isinstance(raw, dict):
        raise ExplorerConfigError("handoffs entry must be a mapping")
    if not raw.get("from") and not raw.get("from_actor"):
        raise ExplorerConfigError("handoff: 'from' or 'from_actor' is required")
    if not raw.get("to") and not raw.get("to_actor"):
        raise ExplorerConfigError("handoff: 'to' or 'to_actor' is required")
    
    from_actor = str(raw.get("from") or raw.get("from_actor"))
    to_actor = str(raw.get("to") or raw.get("to_actor"))
    
    return HandoffSpec(
        from_actor=from_actor,
        to_actor=to_actor,
        channel=str(raw.get("channel") or ""),
        artifact=str(raw.get("artifact") or ""),
        sla=str(raw.get("sla") or ""),
        pain=str(raw.get("pain") or ""),
        docs=_opt_str(raw.get("docs")),
    )


def _parse_to_be(raw: Any) -> ToBeSpec:
    """Parse TO-BE automated solution configuration."""
    if not isinstance(raw, dict):
        raise ExplorerConfigError("views.to_be: must be a mapping")
    
    arch_from_raw = raw.get("architecture_from")
    if isinstance(arch_from_raw, str):
        architecture_from = (arch_from_raw,)
    elif isinstance(arch_from_raw, list):
        architecture_from = tuple(str(s) for s in arch_from_raw)
    else:
        architecture_from = ()
    
    drill_docs_raw = raw.get("drill_docs") or {}
    if not isinstance(drill_docs_raw, dict):
        raise ExplorerConfigError("views.to_be.drill_docs: must be a mapping")
    drill_docs = {str(k): str(v) for k, v in drill_docs_raw.items()}
    
    return ToBeSpec(
        architecture_from=architecture_from,
        runtime_sequence_from=_opt_str(raw.get("runtime_sequence_from")),
        workflow_catalog_from=_opt_str(raw.get("workflow_catalog_from")),
        integrations_from=str(raw.get("integrations_from") or "indexed"),
        drill_docs=drill_docs,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _default_scan_for(project_type: str) -> dict[str, tuple[str, ...]]:
    table = DEFAULT_SCAN_GLOBS.get(project_type) or DEFAULT_SCAN_GLOBS["unknown"]
    return {layer: tuple(globs) for layer, globs in table.items()}


def _detect_project_type(path: Path) -> str:
    """Mirror app.explorer._detect_project_type, but here so we don't import circularly."""
    if not path.is_dir():
        return "unknown"
    if (path / "solution.uipx").exists():
        return "solution"
    if (path / "langgraph.json").exists():
        return "langgraph"
    if (path / "agent_framework.json").exists():
        return "coded-agent"
    if (path / "llama_index.json").exists():
        return "llama-index"
    if (path / "project.json").exists() or any(path.glob("*.uiproj")):
        return "rpa"
    if (path / "pyproject.toml").exists() and any(path.rglob("*.tsx")):
        return "mixed"
    return "unknown"


# ---------------------------------------------------------------------------
# Bootstrap (uipath-claude explore --init)
# ---------------------------------------------------------------------------


STARTER_CONFIG_TEMPLATE = """# UiPlan Explorer config — drives the project view in `uipath-claude explore`.
# Docs: docs/uiplan/EXPLORER.md
project:
  name: "{name}"
  type: {project_type}     # rpa | coded-agent | langgraph | maestro | solution | mixed
  owner: ""
  pdd: ""                  # e.g. docs/PDD-NAME.md

overview:
  summary: |
    Two-three sentences describing what this process does for the business.
  stakeholders: []
  triggers:
    # - {{ kind: http,      description: "POST /endpoint" }}
    # - {{ kind: queue,     description: "Bulk inbound items" }}
    # - {{ kind: scheduled, description: "Nightly close" }}
  actors:
    # - {{ name: "Sales Rep",         role: "submitter" }}
    # - {{ name: "Approver Manager",  role: "human-in-the-loop" }}
  kpis:
    # - {{ label: volume, value: "120 / day" }}
    # - {{ label: p95 SLA, value: "8 minutes" }}

views:
  docs_root: docs/
  as_is:
    # summary_from: docs/process/as-is.md
    # diagram_from: spec.md#business-process-flow
    # actors_from: explorer.actors
    # swimlanes:
    #   - "Sales Rep"
    #   - "Approval Manager"
    # handoffs:
    #   - {{ from: "Sales Rep", to: "Approval Manager", channel: email, artifact: "PDF quote", sla: "2d", pain: "manual chase" }}
    # pain_points: docs/process/pain-points.md
  to_be:
    # architecture_from:
    #   - spec.md#solution-architecture
    #   - plan.md#solution-architecture
    # runtime_sequence_from: plan.md#runtime-sequence
    # workflow_catalog_from: plan.md#workflow-catalog
    # integrations_from: indexed
    # drill_docs:
    #   "Main-Queue.xaml": docs/workflows/main-queue.md
    #   Salesforce: docs/integrations/salesforce.md

indexing:
  # Override defaults below if your repo doesn't match the conventions for `project.type`.
  # scan:
  #   ui:    ["src/**/*.tsx"]
  #   api:   ["backend/**/*.py"]
  #   agent: ["agent/**/*.py"]
  #   rpa:   ["**/*.xaml"]
  exclude:
{exclude_block}
"""


def render_starter_config(project_root: Path) -> str:
    """Render a starter explorer.yaml body for `uipath-claude explore --init`."""
    project_type = _detect_project_type(project_root)
    name = project_root.name or "my-project"
    exclude_block = "\n".join(f"    - \"{g}\"" for g in DEFAULT_EXCLUDES)
    return STARTER_CONFIG_TEMPLATE.format(
        name=name,
        project_type=project_type,
        exclude_block=exclude_block,
    )
