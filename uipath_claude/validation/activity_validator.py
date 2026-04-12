"""Activity validation for UiPath workflows."""
from __future__ import annotations

import re
from pathlib import Path

from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_find_activities


def extract_activity_names_from_xaml(xaml_content: str) -> list[str]:
    """Extract activity names from XAML content.
    
    Finds all XML elements that have a namespace prefix (e.g., ui:LogMessage).
    These represent UiPath activities that need to be validated.
    
    Args:
        xaml_content: XAML file content as string
    
    Returns:
        List of unique activity names with namespace prefixes (e.g., ["ui:LogMessage"])
    """
    if not xaml_content or not xaml_content.strip():
        return []
    
    # Pattern to match XML elements with namespace prefix
    # Matches: <prefix:ActivityName ... or <prefix:ActivityName>
    pattern = r'<([a-zA-Z0-9]+:[a-zA-Z0-9]+)[\s/>]'
    
    matches = re.findall(pattern, xaml_content)
    
    # Return unique activity names, preserving order
    seen = set()
    activities = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            activities.append(match)
    
    return activities


def validate_activities_in_xaml(
    xaml_content: str,
    project_path: str | Path,
    *,
    timeout: int = 60,
) -> dict:
    """Validate that all activities in XAML exist in the project's packages.
    
    Extracts activity names from the XAML and checks them using the
    `uip rpa find-activities` CLI command.
    
    Args:
        xaml_content: XAML file content as string
        project_path: Path to UiPath project directory
        timeout: Command timeout in seconds
    
    Returns dict with:
        - success: bool - True if all activities were found
        - not_found: list[str] - Activity names that don't exist
        - found: list[str] - Activity names that were found
        - error: str - Error message if CLI command failed (optional)
        - raw_output: str - Raw CLI output (optional)
    """
    activities = extract_activity_names_from_xaml(xaml_content)
    
    if not activities:
        return {
            "success": True,
            "found": [],
            "not_found": [],
        }
    
    result = run_uip_rpa_find_activities(
        activity_names=activities,
        project_path=project_path,
        timeout=timeout,
    )
    
    if not result["success"]:
        return {
            "success": False,
            "found": result.get("found", []),
            "not_found": result.get("not_found", activities),
            "error": result.get("error", "Unknown error"),
            "raw_output": result.get("raw_output", ""),
        }
    
    not_found = result.get("not_found", [])
    
    return {
        "success": len(not_found) == 0,
        "found": result.get("found", []),
        "not_found": not_found,
        "raw_output": result.get("raw_output", ""),
    }
