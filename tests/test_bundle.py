import json, pytest
from yosnoop.bundle import build_bundle

def make_home(tmp_path, entries=None):
    home = tmp_path / "agent-c-home"; home.mkdir()
    proj = tmp_path / "proj"; (proj / "docs" / "product").mkdir(parents=True)
    (proj / "docs" / "product" / "state.json").write_text('{"stage":"engineer"}')
    (proj / "docs" / "product" / "backlog.json").write_text("[]")
    (proj / "docs" / "product" / "05-implementation.md").write_text("not copied")
    entries = entries or [{"id": "i1", "slug": "p1", "path": str(proj)}]
    (home / "registry.json").write_text(json.dumps({"version": 1, "entries": entries}))
    for f in ("events.ndjson", "license.json", "notify.json", "mcp-bridge.mjs"):
        (home / f).write_text("x")
    return home, proj

def test_paths_rewritten_into_bundle(tmp_path):
    home, proj = make_home(tmp_path)
    assert build_bundle(home, tmp_path / "out") == 1
    reg = json.loads((tmp_path / "out" / "registry.json").read_text())
    assert reg["entries"][0]["path"] == str(tmp_path / "out" / "projects" / "p1")
    assert (tmp_path / "out" / "projects" / "p1" / "docs" / "product" / "state.json").exists()
    assert not (tmp_path / "out" / "projects" / "p1" / "docs" / "product" / "05-implementation.md").exists()

def test_sensitive_files_never_copied(tmp_path):
    home, _ = make_home(tmp_path)
    build_bundle(home, tmp_path / "out")
    for f in ("license.json", "notify.json", "mcp-bridge.mjs"):
        assert not (tmp_path / "out" / f).exists()
    assert str(tmp_path / "proj") not in (tmp_path / "out" / "registry.json").read_text()

def test_null_and_duplicate_slugs_fall_back_to_id(tmp_path):
    proj = tmp_path / "proj"
    home, _ = make_home(tmp_path, [{"id": "a", "slug": None, "path": str(proj)},
                                   {"id": "b", "slug": "dup", "path": str(proj)},
                                   {"id": "c", "slug": "dup", "path": str(proj)}])
    assert build_bundle(home, tmp_path / "out") == 3
    paths = [e["path"] for e in json.loads((tmp_path / "out" / "registry.json").read_text())["entries"]]
    assert [p.rsplit("/", 1)[1] for p in paths] == ["a", "dup", "c"]

def test_entry_name_cannot_escape_the_bundle(tmp_path):
    proj = tmp_path / "proj"
    home, _ = make_home(tmp_path, [{"id": "../../evil", "slug": None, "path": str(proj)}])
    with pytest.raises(ValueError):
        build_bundle(home, tmp_path / "out")

def test_unreachable_entry_path_is_dropped(tmp_path):
    home, _ = make_home(tmp_path, [{"id": "gone", "slug": "gone", "path": "/nonexistent/x"}])
    assert build_bundle(home, tmp_path / "out") == 0
    reg = json.loads((tmp_path / "out" / "registry.json").read_text())
    assert "/nonexistent/x" not in json.dumps(reg)

def test_spaces_in_ids_become_dashes(tmp_path):
    proj = tmp_path / "proj"
    home, _ = make_home(tmp_path, [{"id": "users-x-code-pickett classroom", "slug": None, "path": str(proj)}])
    assert build_bundle(home, tmp_path / "out") == 1
    assert (tmp_path / "out" / "projects" / "users-x-code-pickett-classroom").is_dir()

def test_path_shaped_parent_ids_are_rewritten(tmp_path):
    proj, child = tmp_path / "proj", tmp_path / "child"; child.mkdir()
    home, _ = make_home(tmp_path, [{"id": "p", "slug": "p", "path": str(proj)},
                                   {"id": "c", "slug": "c", "path": str(child), "parentId": str(proj)},
                                   {"id": "o", "slug": "o", "path": str(child), "parentId": "/Users/x/gone"}])
    build_bundle(home, tmp_path / "out")
    e = json.loads((tmp_path / "out" / "registry.json").read_text())["entries"]
    assert e[1]["parentId"] == str(tmp_path / "out" / "projects" / "p") and e[2]["parentId"] is None

def test_key_shaped_text_in_copied_files_is_redacted(tmp_path):
    home, proj = make_home(tmp_path)
    (home / "events.ndjson").write_text('{"note": "' + "ghp_" + "R" * 36 + '"}\n')
    build_bundle(home, tmp_path / "out")
    assert "ghp_" not in (tmp_path / "out" / "events.ndjson").read_text()
