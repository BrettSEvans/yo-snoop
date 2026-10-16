"""Drive one brain turn for a doctor control, through the production options, and report what happened."""
import json, subprocess, sys
from dataclasses import dataclass, field
from pathlib import Path
from yosnoop import paths


@dataclass
class ControlResult:
    text: str
    error: str | None
    denials: int
    tools_seen: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)


def brain_cmd(dev: bool, *args: str) -> list[str]:
    if dev:
        return [sys.executable, "-m", "yosnoop.brain_main", *args]
    return ["sudo", "-n", "-u", "snoop", str(paths.bin_dir() / "brain"), *args]


def _talk(cmd: list[str], lines: list[dict], timeout: int = 180) -> list[dict]:
    p = subprocess.run(cmd, input="".join(json.dumps(l) + "\n" for l in lines), capture_output=True, text=True,
                       timeout=timeout)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip().startswith("{")]


def credential_line(dev: bool, api_key: str | None) -> dict:
    return {"type": "dev"} if dev else {"type": "key", "value": api_key}


def run_control(prompt: str, dev: bool, api_key: str | None, envprobe: str | None = None) -> ControlResult:
    req = {"type": "control", "prompt": prompt}
    if envprobe:
        req["envprobe"] = envprobe
    try:
        outs = _talk(brain_cmd(dev, "--control"), [credential_line(dev, api_key), req])
    except subprocess.TimeoutExpired:
        return ControlResult("", "timeout", 0)
    r = next((o for o in outs if o.get("type") == "control_result"), None)
    if r is None:
        return ControlResult("", "no-result", 0)
    return ControlResult(r["text"], r["error"], r["denials"], r["tools_seen"], r.get("tools_called", []))


def selftest(dev: bool, targets: list[str]) -> dict:
    outs = _talk(brain_cmd(dev, "--selftest", *targets), [], timeout=60)
    return outs[0] if outs else {"readable": [], "unreadable": []}


def serena_tools(dev: bool) -> dict:
    outs = _talk(brain_cmd(dev, "--serena-tools"), [], timeout=300)
    return outs[0] if outs else {"error": "no-result"}
