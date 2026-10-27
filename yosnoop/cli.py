import sys
from pathlib import Path
from yosnoop.roster import load
from yosnoop import hostcfg

ROSTER = Path(__file__).resolve().parent.parent / "config" / "team.json"

def main(argv: list[str]) -> int:
    if not argv:
        print("usage: ./snoop {setup|prepare|desk|doctor|whoami|voice-setup}"); return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "whoami":
        m = hostcfg.load_host(load(ROSTER)); print(f"Snoop ({m.display_name}) — host {m.email}"); return 0
    if cmd == "setup":
        from yosnoop.setup_mac import run_setup; return run_setup(rest)
    if cmd == "prepare":
        from yosnoop.prepare import prepare
        rep = prepare(dev="--dev" in rest, sync="--no-sync" not in rest)
        print(f"prepare: {'ok' if rep.ok else 'problems'}; registry entries: {rep.bundle_entries}")
        for e in rep.errors:
            print(f"  - {e}")
        return 0 if rep.ok else 1
    if cmd == "voice-setup":
        from yosnoop.desk.voice import fetch, MODEL_DIR
        print(f"Downloading Snoop's voice (Kokoro model + Onyx, ~330 MB) into {MODEL_DIR} …")
        ok = fetch()
        if not ok:
            print("voice-setup: files did not verify; delete models/kokoro and retry"); return 1
        from yosnoop.desk import vosk_wake
        print(f"Downloading the wake-word checker (Vosk small English, ~40 MB) into {vosk_wake.MODEL_DIR} …")
        if not vosk_wake.fetch():
            print("voice-setup: wake-word model did not verify; delete models/vosk and retry"); return 1
        print("voice-setup: ok")
        return 0
    if cmd == "doctor":
        from yosnoop.doctor import run_doctor; return run_doctor(rest)
    if cmd == "desk":
        from yosnoop.desk.run import run_desk; return run_desk(rest)
    print(f"unknown command: {cmd}"); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
