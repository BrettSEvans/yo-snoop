import json, os, subprocess, sys

def run_brain(lines, *args):
    p = subprocess.run([sys.executable, "-m", "yosnoop.brain_main", *args],
                       input="\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines) + "\n",
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

def test_selftest_probes_directories_by_listing(tmp_path):
    d = tmp_path / "d"; d.mkdir(); open_dir = tmp_path / "o"; open_dir.mkdir()
    d.chmod(0o000)
    try:
        out, _ = run_brain([], "--selftest", str(d), str(open_dir), str(tmp_path / "nope"))
    finally:
        d.chmod(0o700)
    assert str(d) in out[0]["unreadable"] and str(open_dir) in out[0]["readable"]
    assert str(tmp_path / "nope") in out[0]["missing"]

def test_malformed_lines_do_not_kill_the_brain():
    out, rc = run_brain(["not json", {"type": "ask"}, {"type": "ask", "id": "2", "question": "q"}])
    assert rc == 0 and [o.get("reason") for o in out] == ["bad-json", "no-credential", "no-credential"]
