from pydantic import BaseModel, ConfigDict, Field

from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalState,
    CommandRegistry,
    FileProposal,
    GenerationGraph,
    GenerationGraphEdge,
    GenerationGraphNode,
    ProposalState,
    StageId,
    StageManifest,
)


class HealthResponse(BaseModel):
    status: str
    routes: list[str]
    metadata: dict[str, str] = Field(default_factory=dict)


class LibraryContextRequest(BaseModel):
    query: str
    top_n: int = 5


class LibraryContextItem(BaseModel):
    book_id: str
    chapter_id: str
    section_id: str
    score: int
    snippet: str
    full_text: str | None = None


class LibraryContextResponse(BaseModel):
    query: str
    items: list[LibraryContextItem]


class ContextSource(BaseModel):
    id: str
    title: str
    kind: str
    category: str
    description: str
    source: str
    available: bool = True


class ContextSourceCategory(BaseModel):
    id: str
    title: str
    description: str
    sources: list[ContextSource]


class ContextSourcesResponse(BaseModel):
    categories: list[ContextSourceCategory]


class DiagramNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    kind: str
    description: str
    x: int
    y: int
    source: str | None = None


class DiagramEdge(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: str
    label: str


class DiagramData(BaseModel):
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)


class LoadDiagramResponse(DiagramData):
    path: str | None = None
    defaulted: bool = False


class SaveDiagramRequest(DiagramData):
    bundle_root: str


class SaveDiagramResponse(DiagramData):
    path: str
    bytes_written: int


class GenerateApprovalPackageRequest(BaseModel):
    bundle_root: str
    graph: GenerationGraph
    stages: list[StageId]
    reviewer: str | None = None


class PackageListResponse(BaseModel):
    packages: list[ApprovalPackageManifest]


class PackageDetailResponse(BaseModel):
    manifest: ApprovalPackageManifest
    approval_state: ApprovalState
    stages: list[StageManifest]
    proposals: list[FileProposal]
