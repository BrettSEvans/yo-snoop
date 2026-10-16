"""One-time privileged setup. Generates one bash script, shows it, runs it under sudo once."""
import getpass, json, os, subprocess
from pathlib import Path
from yosnoop import paths
from yosnoop.roster import load


def setup_script(owner: str, owner_home: str, shared: str) -> str:
    return f"""#!/bin/bash
set -euo pipefail
SHARED="{shared}"
# 0. refuse a pre-planted shared path (symlink, or not a directory owned by the host)
if [ -L "$SHARED" ]; then echo "refusing: $SHARED is a symlink"; exit 1; fi
if [ -e "$SHARED" ] && {{ [ ! -d "$SHARED" ] || [ "$(stat -f %Su "$SHARED")" != "{owner}" ]; }}; then
  echo "refusing: $SHARED exists and is not a directory owned by {owner}"; exit 1
fi
# 1. snoop group and user: own primary group (not staff), hidden, no shell, random throwaway password
dseditgroup -o read snoop >/dev/null 2>&1 || dseditgroup -o create snoop
GID=$(dscl . -read /Groups/snoop PrimaryGroupID | awk '{{print $2}}')
if ! id snoop >/dev/null 2>&1; then
  sysadminctl -addUser snoop -fullName "Snoop Brain" -shell /usr/bin/false -password "$(openssl rand -base64 24)" -home /Users/snoop
  createhomedir -c -u snoop >/dev/null
fi
dscl . create /Users/snoop PrimaryGroupID "$GID"
dscl . create /Users/snoop IsHidden 1
chown -R snoop:snoop /Users/snoop
chmod 700 /Users/snoop
# 2. group that may read the shared knowledge
dseditgroup -o read snoopread >/dev/null 2>&1 || dseditgroup -o create snoopread
dseditgroup -o edit -a snoop -t user snoopread
# 3. shared dirs: created fresh, owner writes, snoop reads; no recursion over existing content
install -d -o {owner} -g snoopread -m 750 "$SHARED" "$SHARED/knowledge" "$SHARED/runtime" "$SHARED/bin"
# 4. the wall: owner's home closed to every other local user
chmod 700 {owner_home}
# 5. owner may start the brain as snoop, nothing else; HOME is snoop's own
TMP=$(mktemp)
printf '%s\\n' 'Defaults>snoop always_set_home' '{owner} ALL=(snoop) NOPASSWD: {shared}/bin/brain' > "$TMP"
visudo -cf "$TMP"
install -m 0440 -o root -g wheel "$TMP" /etc/sudoers.d/snoop
rm -f "$TMP"
echo "snoop setup: done"
"""


def run_setup(argv: list[str]) -> int:
    from yosnoop.cli import ROSTER
    roster = load(ROSTER)
    email = input("Your saasless.ai email (must be in config/team.json): ").strip().lower()
    m = roster.by_email(email)
    if m is None or not m.may_host:
        print(f"{email} is not a roster member who may host"); return 1
    host_json = Path(os.environ["HOME"]) / ".config" / "snoop" / "host.json"
    host_json.parent.mkdir(parents=True, exist_ok=True)
    host_json.write_text(json.dumps({"email": m.email}))
    script = setup_script(getpass.getuser(), os.environ["HOME"], str(paths.shared()))
    print(script)
    if input("Run this once with sudo? Type 'yes': ").strip() != "yes":
        print("not run"); return 1
    f = paths.scratch_dir() / "setup.sh"
    f.write_text(script); f.chmod(0o600)
    rc = subprocess.run(["sudo", "bash", str(f)]).returncode
    f.unlink()
    if rc != 0:
        print(f"setup failed rc={rc}"); return rc
    try:
        from yosnoop.doctor import run_doctor
    except ImportError:  # doctor lands in Plan 1 Task 9
        print("setup done; ./snoop doctor is not built yet"); return 0
    return run_doctor([])
