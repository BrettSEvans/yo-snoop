import json, pathlib, re, subprocess

EXT = pathlib.Path("spikes/extension")

def manifest():
    return json.loads((EXT / "manifest.json").read_text())

def test_only_meet_host_permission():
    m = manifest()
    assert m["manifest_version"] == 3
    assert m["host_permissions"] == ["https://meet.google.com/*"]
    assert m.get("permissions", []) == []
    assert "externally_connectable" not in m and "optional_permissions" not in m
    for cs in m["content_scripts"]:
        assert cs["matches"] == ["https://meet.google.com/*"]

def test_no_input_or_chat_code_paths():
    banned = [r"\.value\s*=", r"dispatchEvent\(", r"KeyboardEvent", r"InputEvent", r"chat", r"sendKeys"]
    for js in EXT.glob("*.js"):
        src = js.read_text()
        for pat in banned:
            assert not re.search(pat, src, re.IGNORECASE), f"{js.name} matches {pat}"
        clicks = re.findall(r"\.click\(\)", src)
        assert len(clicks) <= 1 and (not clicks or "function turnOnCaptions" in src), f"{js.name} clicks outside turnOnCaptions"

def test_local_config_is_ignored():
    # check-ignore needs no file; never write or delete the real config (it holds the live bridge token)
    p = EXT / "config.local.json"
    assert subprocess.run(["git", "check-ignore", "-q", "--no-index", str(p)]).returncode == 0
