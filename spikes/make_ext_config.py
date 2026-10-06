"""Write spikes/extension/config.local.json (gitignored) with a fresh token and the host's card name.
Usage: uv run python -m spikes.make_ext_config --host brett@startup.ai [--port 8790]"""
import argparse, json, secrets
from pathlib import Path
from spikes.common import SECRETS_DIR, sha_prefix
from spikes.roster import load

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); ap.add_argument("--port", type=int, default=8790)
    a = ap.parse_args()
    member = load("config/team.json").by_email(a.host)
    if member is None or not member.may_host:
        raise SystemExit(f"{a.host} is not a roster member who may host")
    token = secrets.token_urlsafe(32)
    (SECRETS_DIR / "bridge-token").write_text(token); (SECRETS_DIR / "bridge-token").chmod(0o600)
    p = Path("spikes/extension/config.local.json")
    p.write_text(json.dumps({"port": a.port, "token": token, "host_display_name": member.display_name}))
    p.chmod(0o600)
    print("wrote config; token sha", sha_prefix(token), "card", f"Snoop ({member.display_name})")

if __name__ == "__main__":
    main()
