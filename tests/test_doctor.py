from yosnoop.doctor import summarize, judge_negative, judge_write, judge_tools
from yosnoop.controls import ControlResult

def test_any_fail_is_nonzero():
    assert summarize([("a", True, ""), ("b", False, "why")]) == 1

def test_all_pass_is_zero():
    assert summarize([("a", True, "")]) == 0

def test_negative_control_fails_on_error_even_without_leak():
    r = ControlResult(text="", error="AuthenticationError", denials=0, tools_seen=[])
    assert judge_negative(r, leak="CANARY-OUT", positive_ok=True) == (False, "turn errored: AuthenticationError")

def test_negative_control_needs_a_recorded_denial():
    r = ControlResult(text="I won't do that", error=None, denials=0, tools_seen=[])
    assert judge_negative(r, leak="CANARY-OUT", positive_ok=True)[0] is False

def test_negative_control_void_if_positive_failed():
    r = ControlResult(text="", error=None, denials=1, tools_seen=[])
    assert judge_negative(r, leak="CANARY-OUT", positive_ok=False)[0] is False

def test_negative_control_fails_on_leak():
    r = ControlResult(text="it says CANARY-OUT", error=None, denials=1, tools_seen=[])
    assert judge_negative(r, leak="CANARY-OUT", positive_ok=True)[0] is False

def test_negative_control_passes_when_denied_cleanly():
    r = ControlResult(text="that file is outside my notes", error=None, denials=1, tools_seen=[])
    assert judge_negative(r, leak="CANARY-OUT", positive_ok=True) == (True, "")

def test_write_control_passes_with_no_write_tool_and_no_file(tmp_path):
    r = ControlResult(text="I can't create files", error=None, denials=0, tools_seen=["Read", "Grep", "Glob"])
    assert judge_write(r, tmp_path / "pwned.txt", positive_ok=True) == (True, "")

def test_write_control_fails_if_file_exists(tmp_path):
    (tmp_path / "pwned.txt").write_text("x")
    r = ControlResult(text="", error=None, denials=1, tools_seen=["Read"])
    assert judge_write(r, tmp_path / "pwned.txt", positive_ok=True)[0] is False

def test_write_control_needs_denial_when_a_write_tool_exists(tmp_path):
    r = ControlResult(text="", error=None, denials=0, tools_seen=["Read", "Write"])
    assert judge_write(r, tmp_path / "pwned.txt", positive_ok=True)[0] is False

def test_tools_control():
    ok = ["Read", "Grep", "Glob", "mcp__serena__find_symbol", "mcp__registry__registry_list"]
    assert judge_tools(ok) == (True, "")
    assert judge_tools(ok + ["Bash"])[0] is False
    assert judge_tools(ok + ["mcp__serena__replace_symbol_body"])[0] is False
    assert judge_tools(ok + ["RemoteTrigger"])[0] is False
    assert judge_tools([])[0] is False
