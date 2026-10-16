import json, stat, pytest
from yosnoop import paths, hostcfg
from yosnoop.roster import load

def test_shared_honors_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SNOOP_SHARED", str(tmp_path / "s"))
    assert paths.shared() == tmp_path / "s"
    assert paths.knowledge_dir() == tmp_path / "s" / "knowledge"
    assert paths.runtime_dir() == tmp_path / "s" / "runtime"
    assert paths.bin_dir() == tmp_path / "s" / "bin"

def test_private_dirs_are_700_and_inside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    for d in (paths.secrets_dir(), paths.scratch_dir()):
        assert str(d).startswith(str(tmp_path)) and stat.S_IMODE(d.stat().st_mode) == 0o700

def test_load_host_accepts_roster_member(tmp_path, monkeypatch):
    p = tmp_path / "host.json"; p.write_text(json.dumps({"email": "jeremy@startup.ai"}))
    monkeypatch.setenv("SNOOP_HOST_JSON", str(p))
    assert hostcfg.load_host(load("config/team.json")).display_name == "Jeremy Leeds"

def test_load_host_rejects_non_member(tmp_path, monkeypatch):
    p = tmp_path / "host.json"; p.write_text(json.dumps({"email": "x@startup.ai"}))
    monkeypatch.setenv("SNOOP_HOST_JSON", str(p))
    with pytest.raises(SystemExit):
        hostcfg.load_host(load("config/team.json"))
