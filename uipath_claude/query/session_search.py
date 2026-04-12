"""Utilities for searching in-session chat history."""


def search_session_history(
    history: list[dict[str, str]],
    query: str,
    limit: int = 5,
) -> list[dict[str, str]]:
    """Search chat history entries by content, returning most recent matches first."""
    normalized_query = query.strip().lower()
    if not normalized_query or limit <= 0:
        return []

    matches: list[dict[str, str]] = []
    for message in reversed(history):
        content = message.get("content", "")
        if normalized_query in content.lower():
            matches.append(message)
            if len(matches) >= limit:
                break

    return matches
