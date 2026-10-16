import shutil, subprocess
from pathlib import Path

AGENT_C = Path.home() / "Code" / "Saasless" / "Agent-C"
SERENA_PIN = "serena-agent==2.0.0"  # first release with the #1938 read_only fix


def brain_wrapper(runtime: Path, knowledge: Path) -> str:
    return (f"#!/bin/sh\nexport HOME=/Users/snoop\ncd {knowledge}\n"
            f"exec {runtime}/.venv/bin/python -m yosnoop.brain_main \"$@\"\n")


def serena_cmd(runtime: Path, project: Path) -> list[str]:
    from yosnoop.serena_cfg import START_ARGS
    # run under /usr/bin/env: the PATH gives Serena the runtime's node/npm, never the host's
    return [f"PATH={runtime / 'node' / 'bin'}:/usr/bin:/bin", str(runtime / "serena-venv" / "bin" / "serena"),
            *START_ARGS, "--project", str(project)]


def copy_node(runtime: Path, node_bin: Path) -> None:
    """node + npm only, outside any home (Serena's TypeScript server needs both on PATH as snoop)."""
    src = Path(node_bin).resolve().parent.parent
    dest = runtime / "node"
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "bin").mkdir(parents=True)
    shutil.copy2(src / "bin" / "node", dest / "bin" / "node")
    shutil.copytree(src / "lib" / "node_modules" / "npm", dest / "lib" / "node_modules" / "npm", symlinks=True)
    for name, target in (("npm", "npm-cli.js"), ("npx", "npx-cli.js")):
        (dest / "bin" / name).symlink_to(Path("..") / "lib" / "node_modules" / "npm" / "bin" / target)


def _interpreter(py: Path) -> Path:
    found = sorted(py.glob("cpython-3.12.*/bin/python3.12"))
    return found[-1] if found else py


def sync_runtime(repo_root: Path, runtime: Path, runner=subprocess.run, copy_files: bool = True) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    py = runtime / "python"
    runner(["uv", "python", "install", "3.12", "--install-dir", str(py)], check=True)
    interp = _interpreter(py)
    runner(["uv", "venv", "--python", str(interp), "--allow-existing", str(runtime / ".venv")], check=True)
    runner(["uv", "pip", "install", "--python", str(runtime / ".venv" / "bin" / "python"), str(repo_root)], check=True)
    # Serena pins exact deps that clash with ours, so it gets its own venv
    runner(["uv", "venv", "--python", str(interp), "--allow-existing", str(runtime / "serena-venv")], check=True)
    runner(["uv", "pip", "install", "--python", str(runtime / "serena-venv" / "bin" / "python"), SERENA_PIN], check=True)
    if not copy_files:
        return
    node = shutil.which("node")
    if node:
        copy_node(runtime, Path(node))
    reg = AGENT_C / "registry-mcp"
    if (reg / "out").exists():
        dest = runtime / "registry-mcp"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(reg / "out", dest / "out")
        shutil.copytree(reg / "node_modules", dest / "node_modules", symlinks=True)
        shutil.copy2(reg / "package.json", dest / "package.json")
