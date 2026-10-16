from yosnoop import gate

def k(*parts): return "".join(parts)

def test_clean_answer_passes():
    r = gate.gate("Three PRs merged yesterday; CI is green on main.")
    assert r.allowed and r.text.startswith("Three PRs")

def test_anthropic_key_blocks():
    r = gate.gate("the key is " + k("sk-", "ant-", "api03-", "A" * 90))
    assert not r.allowed and r.text == "Snoop here, can't share that one."

def test_github_tokens_block():
    for t in (k("ghp_", "B" * 36), k("github_", "pat_", "C" * 70)):
        assert not gate.gate(t).allowed

def test_aws_private_key_and_service_account_block():
    assert not gate.gate(k("AKIA", "D" * 16)).allowed
    assert not gate.gate(k("-----BEGIN ", "PRIVATE KEY-----")).allowed
    assert not gate.gate('{"type": "service_account", "private_key_id": "' + "e" * 40 + '"}').allowed

def test_google_api_key_blocks():
    assert not gate.gate(k("AI", "za", "Sy", "F" * 33)).allowed

def test_scanner_crash_blocks(monkeypatch):
    monkeypatch.setattr(gate, "scan", lambda t: (_ for _ in ()).throw(RuntimeError("boom")))
    r = gate.gate("anything")
    assert not r.allowed and r.reason == "scanner-error"

def test_redact_replaces_key_shaped_text():
    t = "token " + k("ghp_", "Q" * 36) + " ok"
    assert gate.redact(t) == "token [REDACTED] ok" and gate.gate(gate.redact(t)).allowed
