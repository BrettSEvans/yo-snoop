import json
from yosnoop.brain_opts import build_options, REGISTRY_READ_TOOLS, KEY_STRIP, BASE_TOOLS

def test_isolation_options(tmp_path):
    o = build_options(tmp_path, None, None, "claude-sonnet-5-5")
    assert o.setting_sources == [] and o.strict_mcp_config is True
    assert o.permission_mode == "dontAsk" and o.max_turns == 15 and str(o.cwd) == str(tmp_path)
    assert json.loads(o.settings)["permissions"]["blockReadsOutsideWorkingDirectories"] is True

def test_base_tools_are_an_allowlist_of_three(tmp_path):
    o = build_options(tmp_path, None, None, "m")
    assert o.tools == BASE_TOOLS == ["Read", "Grep", "Glob"]

def test_no_bare_read_allow_and_no_bash(tmp_path):
    o = build_options(tmp_path, None, None, "m")
    for bare in ("Read", "Grep", "Glob", "Bash"):
        assert bare not in o.allowed_tools
    for t in ("Bash", "WebFetch", "WebSearch", "Write", "Edit", "NotebookEdit", "Task"):
        assert t in o.disallowed_tools

def test_mcp_servers_strip_the_key(tmp_path):
    o = build_options(tmp_path, ["node", "out/index.js"], ["serena", "start-mcp-server"], "m")
    for name in ("registry", "serena"):
        s = o.mcp_servers[name]
        assert [s["command"], *s["args"][:2]] == KEY_STRIP
    assert {f"mcp__registry__{t}" for t in REGISTRY_READ_TOOLS} <= set(o.allowed_tools)
    assert "mcp__registry__stage_approve" not in o.allowed_tools

def test_key_goes_only_to_cli_env(tmp_path):
    o = build_options(tmp_path, None, None, "m", api_key="KEY")
    assert o.env == {"ANTHROPIC_API_KEY": "KEY"}
