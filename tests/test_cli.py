import json
from yosnoop.cli import main

def test_whoami_prints_card(tmp_path, monkeypatch, capsys):
    p = tmp_path / "host.json"; p.write_text(json.dumps({"email": "brett@startup.ai"}))
    monkeypatch.setenv("SNOOP_HOST_JSON", str(p))
    assert main(["whoami"]) == 0
    assert "Snoop (Brett Evans)" in capsys.readouterr().out

def test_unknown_command_is_error():
    assert main(["fly"]) == 2
