import json
from yosnoop.cli import main

def test_whoami_prints_card(tmp_path, monkeypatch, capsys):
    p = tmp_path / "host.json"; p.write_text(json.dumps({"email": "brett@startup.ai"}))
    monkeypatch.setenv("SNOOP_HOST_JSON", str(p))
    assert main(["whoami"]) == 0
    assert "Snoop (Brett Evans)" in capsys.readouterr().out

def test_unknown_command_is_error():
    assert main(["fly"]) == 2

def test_voice_setup_fetches_voice_and_wake_model(monkeypatch, capsys):
    from yosnoop.desk import voice, vosk_wake
    calls = []
    monkeypatch.setattr(voice, "fetch", lambda: calls.append("kokoro") or True)
    monkeypatch.setattr(vosk_wake, "fetch", lambda: calls.append("vosk") or True)
    assert main(["voice-setup"]) == 0
    assert calls == ["kokoro", "vosk"] and "voice-setup: ok" in capsys.readouterr().out

def test_voice_setup_fails_if_wake_model_does_not_verify(monkeypatch):
    from yosnoop.desk import voice, vosk_wake
    monkeypatch.setattr(voice, "fetch", lambda: True)
    monkeypatch.setattr(vosk_wake, "fetch", lambda: False)
    assert main(["voice-setup"]) == 1
