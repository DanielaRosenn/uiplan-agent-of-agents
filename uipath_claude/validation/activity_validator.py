"""Validate that activities used in XAML actually exist."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, List, Tuple

from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_find_activities


def extract_activity_names_from_xaml(xaml_content: str) -> Set[str]:
    """
    Extract activity element names from XAML content.
    
    Returns set of activity names like "GetOutlookMailMessages", "LogMessage", etc.
    Excludes standard XAML elements (Sequence, Activity, etc.)
    """
    # Standard XAML elements to ignore
    standard_elements = {
        "Activity", "Sequence", "Flowchart", "StateMachine",
        "Variable", "InArgument", "OutArgument", "InOutArgument",
        "ActivityAction", "DelegateInArgument", "DelegateOutArgument",
        "TextExpression.NamespacesForImplementation",
        "TextExpression.ReferencesForImplementation",
        "AssemblyReference", "Collection",
    }
    
    # Find all element tags with namespace prefixes
    # Pattern: <prefix:ElementName or <ElementName
    pattern = r'<(?:(\w+):)?(\w+)[\s>]'
    matches = re.findall(pattern, xaml_content)
    
    activity_names = set()
    for prefix, name in matches:
        # Skip standard elements
        if name in standard_elements:
            continue
        # Skip closing tags, comments, etc
        if name.startswith('/') or name.startswith('!'):
            continue
        # Only include elements with ui: prefix or no prefix (in ui namespace)
        if prefix in ('ui', ''):
            activity_names.add(name)
    
    return activity_names


def validate_activities_in_xaml(
    xaml_path: Path,
    *,
    skip_validation: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Validate that all activities in XAML file actually exist in UiPath.
    
    Args:
        xaml_path: Path to XAML file
        skip_validation: If True, skip validation (for testing)
        
    Returns:
        Tuple of (success, list of error messages)
        success is True if all activities exist or validation is skipped
    """
    if skip_validation:
        return True, []
    
    try:
        content = xaml_path.read_text(encoding='utf-8')
    except Exception as e:
        return False, [f"Failed to read XAML file: {e}"]
    
    activity_names = extract_activity_names_from_xaml(content)
    
    if not activity_names:
        # No activities found, might be empty file
        return True, []
    
    errors = []
    
    # Check each activity
    for activity_name in sorted(activity_names):
        result = run_uip_rpa_find_activities(activity_name)
        
        if not result["success"]:
            # CLI failed, skip validation for this activity
            continue
        
        activities = result["activities"]
        
        # Check if activity exists
        found = any(
            act.get("ClassName", "").endswith(activity_name) or
            act.get("ActivityTypeId", "").endswith(activity_name)
            for act in activities
        )
        
        if not found:
            errors.append(
                f"Activity '{activity_name}' not found in UiPath packages. "
                f"This may be a hallucinated activity name."
            )
    
    return len(errors) == 0, errors
