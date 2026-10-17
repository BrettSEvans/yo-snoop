import json, re, shutil
from yosnoop.gate import redact_file
from pathlib import Path

TOP_FILES = ("registry.json", "events.ndjson", "runs.json", "recent.json")
PROJECT_GLOBS = ("docs/**/state.json", "docs/product/backlog*.json", "docs/product/attribution.json")
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _name(e: dict, used: set[str]) -> str:
    name = e.get("slug") or e["id"]
    if name in used:  # duplicate slugs fall back to the (unique) id
        name = e["id"]
    if ".." in name or name.startswith("."):
        raise ValueError(f"unsafe registry entry name: {name!r}")
    name = _UNSAFE.sub("-", name)
    used.add(name)
    return name


def build_bundle(agent_c_home: Path, dest: Path) -> int:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for f in TOP_FILES:
        if (agent_c_home / f).exists():
            shutil.copy2(agent_c_home / f, dest / f)
    reg = json.loads((dest / "registry.json").read_text())
    n, used, moved = 0, set(), {}
    for e in reg.get("entries", []):
        target = dest / "projects" / _name(e, used)
        src = Path(e.get("path") or "")
        if e.get("path"):
            moved[e["path"]] = str(target)
        e["path"] = str(target)  # never leave a host path in the bundle
        if not e.get("path") or not src.is_dir():
            continue
        for pat in PROJECT_GLOBS:
            for f in src.glob(pat):
                if f.is_symlink() or not f.is_file():
                    continue
                o = target / f.relative_to(src)
                o.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, o)
        n += 1
    for e in reg.get("entries", []):  # parentId may be a host path; point it into the bundle
        pid = e.get("parentId")
        if isinstance(pid, str) and pid.startswith("/"):
            e["parentId"] = moved.get(pid)
    (dest / "registry.json").write_text(json.dumps(reg, indent=1))
    for f in dest.rglob("*"):  # nothing key-shaped reaches the brain
        if f.is_file():
            redact_file(f)
    return n
