import json, os, subprocess, sys

def run_brain(lines, *args):
    p = subprocess.run([sys.executable, "-m", "yosnoop.brain_main", *args], input="\n".join(map(json.dumps, lines)) + "\n",
                       capture_output=True, text=True, timeout=30)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()], p.returncode

def test_ask_before_credential_is_refused():
    out, _ = run_brain([{"type": "ask", "id": "1", "question": "hi", "asker": "a", "room": "team"}])
    assert out[0] == {"type": "error", "id": "1", "reason": "no-credential"}

def test_selftest_reports_unreadable(tmp_path):
    secret = tmp_path / "s"; secret.write_text("x"); secret.chmod(0o000)
    out, rc = run_brain([], "--selftest", str(secret))
    assert rc == 0 and str(secret) in out[0]["unreadable"]

def test_key_never_enters_process_environment():
    src = open("yosnoop/brain_main.py").read()
    assert "os.environ[" not in src and "putenv" not in src
