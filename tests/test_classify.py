from hades.classify import classify_project


def test_human_project_uses_last_path_segment():
    display, kind = classify_project("/Users/me/projects/hades")
    assert display == "hades"
    assert kind == "human"


def test_agent_marker_path_is_classified_as_agent():
    display, kind = classify_project("/Users/me/.claude-mem/observer-sessions")
    assert display == "claude-mem"
    assert kind == "agent"


def test_empty_path_falls_back_to_itself():
    display, kind = classify_project("")
    assert display == ""
    assert kind == "human"


def test_trailing_slash_path_falls_back_to_full_path():
    display, kind = classify_project("/Users/me/projects/hades/")
    assert display == "/Users/me/projects/hades/"
    assert kind == "human"
