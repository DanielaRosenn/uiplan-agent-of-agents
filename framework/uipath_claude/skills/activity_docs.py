"""Activity documentation lookup from UiPath/skills repo."""
from pathlib import Path
from typing import Optional
import re


def get_activity_docs_path() -> Optional[Path]:
    """Get the path to the activity-docs folder in the skills repo."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            docs_path = current / "skills" / "references" / "activity-docs"
            if docs_path.exists():
                return docs_path
        current = current.parent
    return None


def list_available_packages() -> list[str]:
    """List all packages with activity documentation."""
    docs_path = get_activity_docs_path()
    if not docs_path:
        return []
    
    return sorted([
        d.name for d in docs_path.iterdir()
        if d.is_dir() and d.name.startswith("UiPath.")
    ])


def get_package_versions(package_id: str) -> list[str]:
    """Get available documentation versions for a package."""
    docs_path = get_activity_docs_path()
    if not docs_path:
        return []
    
    package_path = docs_path / package_id
    if not package_path.exists():
        return []
    
    return sorted([
        d.name for d in package_path.iterdir()
        if d.is_dir() and re.match(r"^\d+\.\d+", d.name)
    ], key=lambda v: [int(x) for x in v.split(".")], reverse=True)


def get_latest_version(package_id: str) -> Optional[str]:
    """Get the latest documentation version for a package."""
    versions = get_package_versions(package_id)
    return versions[0] if versions else None


def get_activity_doc(package_id: str, activity_name: str, version: Optional[str] = None) -> Optional[str]:
    """
    Get documentation for a specific activity.
    
    Args:
        package_id: Package ID (e.g., "UiPath.Mail.Activities")
        activity_name: Activity name (e.g., "GetOutlookMailMessages")
        version: Specific version or None for latest
        
    Returns:
        Documentation content or None if not found
    """
    docs_path = get_activity_docs_path()
    if not docs_path:
        return None
    
    if version is None:
        version = get_latest_version(package_id)
    if not version:
        return None
    
    # Try activities folder first
    activity_file = docs_path / package_id / version / "activities" / f"{activity_name}.md"
    if activity_file.exists():
        return activity_file.read_text()
    
    # Try coded folder
    coded_file = docs_path / package_id / version / "coded" / f"{activity_name}.md"
    if coded_file.exists():
        return coded_file.read_text()
    
    return None


def get_package_overview(package_id: str, version: Optional[str] = None) -> Optional[str]:
    """
    Get the overview documentation for a package.
    
    Args:
        package_id: Package ID (e.g., "UiPath.Mail.Activities")
        version: Specific version or None for latest
        
    Returns:
        Overview content or None if not found
    """
    docs_path = get_activity_docs_path()
    if not docs_path:
        return None
    
    if version is None:
        version = get_latest_version(package_id)
    if not version:
        return None
    
    overview_file = docs_path / package_id / version / "activities" / "overview.md"
    if overview_file.exists():
        return overview_file.read_text()
    
    return None


def list_activities(package_id: str, version: Optional[str] = None) -> list[str]:
    """
    List all documented activities for a package.
    
    Args:
        package_id: Package ID
        version: Specific version or None for latest
        
    Returns:
        List of activity names
    """
    docs_path = get_activity_docs_path()
    if not docs_path:
        return []
    
    if version is None:
        version = get_latest_version(package_id)
    if not version:
        return []
    
    activities = []
    
    # Check activities folder
    activities_path = docs_path / package_id / version / "activities"
    if activities_path.exists():
        for f in activities_path.glob("*.md"):
            if f.name != "overview.md":
                activities.append(f.stem)
    
    # Check coded folder
    coded_path = docs_path / package_id / version / "coded"
    if coded_path.exists():
        for f in coded_path.glob("*.md"):
            activities.append(f.stem)
    
    return sorted(set(activities))


def search_activities(query: str) -> list[dict]:
    """
    Search for activities across all packages.
    
    Args:
        query: Search query (case-insensitive)
        
    Returns:
        List of matching activities with package info
    """
    results = []
    query_lower = query.lower()
    
    for package_id in list_available_packages():
        version = get_latest_version(package_id)
        if not version:
            continue
        
        for activity in list_activities(package_id, version):
            if query_lower in activity.lower():
                results.append({
                    "package": package_id,
                    "version": version,
                    "activity": activity,
                })
    
    return results
