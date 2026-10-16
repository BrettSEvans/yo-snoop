"""Host-side preparation of the brain's runtime and knowledge. Runs as the host, never as snoop."""
import asyncio, json, os
from dataclasses import dataclass, field
from pathlib import Path
from yosnoop import paths
from yosnoop.runtime_sync import sync_runtime, brain_wrapper, serena_cmd as make_serena_cmd
from yosnoop.refresher import Refresher
from yosnoop.bundle import build_bundle
from yosnoop.serena_cfg import project_yml, list_tools, assert_tools

ORIGIN = "https://github.com/brett-saasless/Agent-C.git"
REPO_ROOT = Path(__file__).resolve().parent.parent


def prepare_config(knowledge: Path, bundle_built: bool, runtime: Path, serena_cmd, persona: str,
                   model: str = "claude-sonnet-5-5") -> dict:
    cfg = {"model": model, "persona": persona}
    if serena_cmd:
        cfg["serena_cmd"] = serena_cmd
    if bundle_built:
        cfg["registry_cmd"] = [str(runtime / "node" / "bin" / "node"), str(runtime / "registry-mcp" / "out" / "index.js")]
    return cfg


def load_persona() -> str:
    f = Path(os.environ["HOME"]) / ".claude" / "output-styles" / "snoop.md"
    return (f.read_text() if f.exists() else "") + "\nNo curse words."


@dataclass
class PrepReport:
    ok: bool
    bundle_entries: int | None = None
    errors: list[str] = field(default_factory=list)


def prepare(dev: bool = False, sync: bool = True) -> PrepReport:
    k, rt, b = paths.knowledge_dir(), paths.runtime_dir(), paths.bin_dir()
    errors: list[str] = []
    if sync:
        sync_runtime(REPO_ROOT, rt)
    wrapper = b / "brain"
    wrapper.write_text(brain_wrapper(rt, k)); wrapper.chmod(0o750)
    rep = Refresher(ORIGIN, k).refresh()
    errors += rep.errors
    agent_c_home, n = Path(os.environ["HOME"]) / ".agent-c", None
    if (agent_c_home / "registry.json").exists():
        n = build_bundle(agent_c_home, k / "agent-c-home")
    (k / "empty-projects").mkdir(exist_ok=True)
    (k / ".serena").mkdir(exist_ok=True)
    (k / ".serena" / "project.yml").write_text(project_yml("agent-c"))
    scmd = make_serena_cmd(rt, k)
    try:
        # Host-side first run: Serena autofills project.yml (it cannot write it later as snoop) and we check its tools
        assert_tools(asyncio.run(list_tools(["/usr/bin/env", *scmd])))
    except Exception as e:
        errors.append(f"serena: {type(e).__name__}: {e}")
        scmd = None
    cfg = prepare_config(k, n is not None, rt, scmd, load_persona())
    (k / "brain-config.json").write_text(json.dumps(cfg, indent=1))
    return PrepReport(ok=not errors, bundle_entries=n, errors=errors)
