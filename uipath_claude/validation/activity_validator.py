"""Activity validation for UiPath workflows."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set, Tuple

from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_find_activities


def extract_activity_names_from_xaml(xaml_content: str) -> Set[str]:
    """Extract activity names from XAML content.
    
    Finds all XML elements that have a namespace prefix (e.g., ui:LogMessage).
    These represent UiPath activities that need to be validated.
    
    Args:
        xaml_content: XAML file content as string
    
    Returns:
        Set of unique activity names with namespace prefixes (e.g., {"ui:LogMessage"})
    """
    if not xaml_content or not xaml_content.strip():
        return set()
    
    # Pattern to match XML elements with namespace prefix
    # Matches: <prefix:ActivityName ... or <prefix:ActivityName>
    pattern = r'<([a-zA-Z0-9]+:[a-zA-Z0-9]+)[\s/>]'
    
    matches = re.findall(pattern, xaml_content)
    
    return set(matches)


def validate_activities_in_xaml(
    xaml_path: Path,
    *,
    skip_validation: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate that all activities in XAML exist in available packages.
    
    Extracts activity names from the XAML file and checks them using the
    `uip rpa find-activities` CLI command.
    
    Args:
        xaml_path: Path to the XAML file
        skip_validation: If True, skip validation and return success
    
    Returns:
        Tuple of (success: bool, invalid_activities: List[str])
        - success: True if all activities were found or validation was skipped
        - invalid_activities: List of activity names that don't exist
    """
    if skip_validation:
        return (True, [])
    
    xaml_content = xaml_path.read_text(encoding="utf-8")
    activities = extract_activity_names_from_xaml(xaml_content)
    
    if not activities:
        return (True, [])
    
    invalid_activities = []
    
    for activity in activities:
        result = run_uip_rpa_find_activities(query=activity)
        
        if not result["success"]:
            continue
        
        if not result.get("found", False):
            invalid_activities.append(activity)
    
    return (len(invalid_activities) == 0, invalid_activities)
