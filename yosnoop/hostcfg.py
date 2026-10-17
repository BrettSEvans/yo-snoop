import json, os
from pathlib import Path
from yosnoop.roster import Member, Roster

def host_json_path() -> Path:
    return Path(os.environ.get("SNOOP_HOST_JSON", Path(os.environ["HOME"]) / ".config" / "snoop" / "host.json"))

def load_host(roster: Roster) -> Member:
    p = host_json_path()
    if not p.exists():
        raise SystemExit(f"no host config at {p}; run ./snoop setup")
    email = json.loads(p.read_text())["email"]
    m = roster.by_email(email)
    if m is None or not m.may_host:
        raise SystemExit(f"{email} is not a roster member who may host (config/team.json)")
    return m
