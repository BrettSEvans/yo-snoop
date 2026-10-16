from pathlib import Path
from yosnoop.runtime_sync import sync_runtime, brain_wrapper, SERENA_PIN, serena_cmd

def test_wrapper_sets_home_and_cwd_and_never_names_a_host_home():
    w = brain_wrapper(Path("/Users/Shared/snoop/runtime"), Path("/Users/Shared/snoop/knowledge"))
    assert w.startswith("#!/bin/sh\n")
    assert "export HOME=/Users/snoop" in w
    assert "cd /Users/Shared/snoop/knowledge" in w
    assert "exec /Users/Shared/snoop/runtime/.venv/bin/python -m yosnoop.brain_main" in w
    assert "$HOME" not in w.split("export HOME=/Users/snoop", 1)[1] and "~" not in w

def test_sync_uses_a_python_outside_any_home(tmp_path):
    calls = []
    sync_runtime(Path.cwd(), tmp_path / "runtime", runner=lambda cmd, **k: calls.append(cmd))
    flat = [" ".join(map(str, c)) for c in calls]
    assert any("uv python install 3.12 --install-dir" in c and str(tmp_path) in c for c in flat)
    assert any("uv venv" in c and "--python" in c for c in flat)

def test_serena_gets_its_own_pinned_venv(tmp_path):
    calls = []
    rt = tmp_path / "runtime"
    sync_runtime(Path.cwd(), rt, runner=lambda cmd, **k: calls.append(cmd))
    flat = [" ".join(map(str, c)) for c in calls]
    assert SERENA_PIN == "serena-agent==2.0.0"
    assert any(str(rt / "serena-venv") in c and SERENA_PIN in c for c in flat)
    assert serena_cmd(rt)[0] == str(rt / "serena-venv" / "bin" / "serena")
