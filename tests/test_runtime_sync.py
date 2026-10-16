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
    sync_runtime(Path.cwd(), tmp_path / "runtime", runner=lambda cmd, **k: calls.append(cmd), copy_files=False)
    flat = [" ".join(map(str, c)) for c in calls]
    assert any("uv python install 3.12 --install-dir" in c and str(tmp_path) in c for c in flat)
    assert any("uv venv" in c and "--python" in c for c in flat)

def test_serena_gets_its_own_pinned_venv(tmp_path):
    calls = []
    rt = tmp_path / "runtime"
    sync_runtime(Path.cwd(), rt, runner=lambda cmd, **k: calls.append(cmd), copy_files=False)
    flat = [" ".join(map(str, c)) for c in calls]
    assert SERENA_PIN == "serena-agent==2.0.0"
    assert any(str(rt / "serena-venv") in c and SERENA_PIN in c for c in flat)
    c = serena_cmd(rt, tmp_path / "k")
    assert c[0] == f"PATH={rt / 'node' / 'bin'}:/usr/bin:/bin"
    assert c[1] == str(rt / "serena-venv" / "bin" / "serena") and c[-2:] == ["--project", str(tmp_path / "k")]
    assert "ide" in c

def test_copy_node_takes_only_node_and_npm(tmp_path):
    from yosnoop.runtime_sync import copy_node
    src = tmp_path / "nvm" / "v1"; (src / "bin").mkdir(parents=True)
    (src / "bin" / "node").write_text("bin"); (src / "bin" / "node").chmod(0o755)
    for pkg in ("npm", "openclaw"):
        (src / "lib" / "node_modules" / pkg / "bin").mkdir(parents=True)
    (src / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js").write_text("x")
    (src / "lib" / "node_modules" / "npm" / "bin" / "npx-cli.js").write_text("x")
    rt = tmp_path / "rt"
    copy_node(rt, src / "bin" / "node")
    assert (rt / "node" / "bin" / "node").read_text() == "bin"
    assert (rt / "node" / "bin" / "npm").resolve() == (rt / "node" / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js").resolve()
    assert not (rt / "node" / "lib" / "node_modules" / "openclaw").exists()
