"""Expose bundled activity-docs as MCP resources (package overviews + sample activities)."""
from __future__ import annotations

from mcp.types import Resource

from mcp.server.lowlevel.helper_types import ReadResourceContents

from uipath_claude.skills.activity_docs import (
    get_activity_doc,
    get_latest_version,
    get_package_overview,
    list_activities,
    list_available_packages,
)

_MAX_PACKAGES = 40
_MAX_ACTIVITIES_PER_PACKAGE = 12


async def get_doc_resources() -> list[Resource]:
    resources: list[Resource] = []
    packages = list_available_packages()[:_MAX_PACKAGES]
    for package_id in packages:
        version = get_latest_version(package_id)
        if not version:
            continue
        resources.append(
            Resource(
                uri=f"uipath://doc/{package_id}/overview",
                name=f"{package_id} overview",
                description=f"Overview for {package_id} ({version})",
                mimeType="text/markdown",
            )
        )
        for activity in list_activities(package_id, version)[:_MAX_ACTIVITIES_PER_PACKAGE]:
            resources.append(
                Resource(
                    uri=f"uipath://doc/{package_id}/{activity}",
                    name=f"{package_id}/{activity}",
                    description=f"Activity doc {activity}",
                    mimeType="text/markdown",
                )
            )
    return resources


async def fetch_doc_resource(uri: str) -> list[ReadResourceContents]:
    raw = str(uri)
    if not raw.startswith("uipath://doc/"):
        return [
            ReadResourceContents(
                content=f"Unsupported doc URI: {uri}",
                mime_type="text/plain",
            )
        ]
    rest = raw[len("uipath://doc/") :]
    parts = rest.split("/", 1)
    if len(parts) != 2:
        return [ReadResourceContents(content="Invalid doc URI", mime_type="text/plain")]
    package_id, item = parts
    if item == "overview":
        text = get_package_overview(package_id) or "No overview"
    else:
        text = get_activity_doc(package_id, item) or f"No doc for {package_id}/{item}"
    return [ReadResourceContents(content=text, mime_type="text/markdown")]
