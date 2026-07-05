AGENT_PATH_MARKERS: dict[str, str] = {
    ".claude-mem": "claude-mem",
}


def classify_project(project_path: str) -> tuple[str, str]:
    """Return (display_name, session_type) for a session's project path.

    session_type is "agent" for known background tooling (observers, hooks, ...),
    "human" for regular interactive project sessions.
    """
    for marker, label in AGENT_PATH_MARKERS.items():
        if marker in project_path:
            return label, "agent"
    return project_path.split("/")[-1] or project_path, "human"
