import pytest
from yosnoop.serena_cfg import KEEP, REMOVED, ALL_KNOWN, START_ARGS, project_yml, assert_tools

def test_keep_is_read_only_subset():
    assert {"read_file", "find_symbol", "find_referencing_symbols"} <= KEEP
    assert not ({"replace_symbol_body", "execute_shell_command", "serena_repl", "write_memory"} & KEEP)
    assert KEEP < ALL_KNOWN

def test_project_yml_is_read_only_allowlist():
    y = project_yml("agent-c")
    assert "read_only: true" in y and "fixed_tools:" in y and "excluded_tools" not in y
    for t in KEEP:
        assert f"- {t}" in y
    for t in REMOVED:
        assert f"- {t}" not in y

def test_starts_only_in_the_ide_context_with_no_dashboard():
    assert START_ARGS[START_ARGS.index("--context") + 1] == "ide"
    assert START_ARGS[START_ARGS.index("--enable-web-dashboard") + 1] == "False"
    assert "safe_delete_symbol" in REMOVED

def test_assert_tools_passes_on_exact_keep():
    assert_tools(set(KEEP))

def test_assert_tools_refuses_an_editing_tool():
    with pytest.raises(RuntimeError, match="replace_symbol_body"):
        assert_tools(set(KEEP) | {"replace_symbol_body"})
