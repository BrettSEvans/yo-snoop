import json, subprocess
from pathlib import Path
from yosnoop.refresher import Refresher

def make_origin(tmp_path) -> str:
    src = tmp_path / "src"; src.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(src)], check=True)
    (src / "README.md").write_text("hello\n")
    subprocess.run(["git", "-C", str(src), "add", "."], check=True)
    subprocess.run(["git", "-C", str(src), "-c", "user.email=t@t", "-c", "user.name=Tess", "commit", "-qm", "init readme"], check=True)
    subprocess.run(["git", "-C", str(src), "branch", "feat/x"], check=True)
    return str(src)

def fake_gh(args):
    return json.dumps([{"number": 7, "title": "Add thing", "state": "OPEN"}]) if args[0] == "pr" else json.dumps([{"headBranch": "main", "conclusion": "success"}])

def fake_repomix(clone: Path, out: Path):
    out.write_text("<repo>README.md: hello</repo>")

def test_refresh_writes_clone_facts_status_and_map(tmp_path):
    rep = Refresher(make_origin(tmp_path), tmp_path / "k", gh=fake_gh, repomix=fake_repomix).refresh()
    assert rep.ok and not rep.map_blocked
    facts = (tmp_path / "k" / "git-facts.txt").read_text()
    assert "origin/feat/x" in facts and "init readme" in facts and "README.md" in facts and "Tess" in facts
    st = json.loads((tmp_path / "k" / "pr-ci-status.json").read_text())
    assert st["pull_requests"][0]["number"] == 7 and st["runs"][0]["conclusion"] == "success"
    assert (tmp_path / "k" / "repo-map.xml").exists()

def test_map_with_secret_is_blocked_and_removed(tmp_path):
    bad = lambda clone, out: out.write_text("token " + "ghp_" + "Z" * 36)
    rep = Refresher(make_origin(tmp_path), tmp_path / "k", gh=fake_gh, repomix=bad).refresh()
    assert rep.map_blocked and not (tmp_path / "k" / "repo-map.xml").exists()

def test_second_refresh_fetches(tmp_path):
    r = Refresher(make_origin(tmp_path), tmp_path / "k", gh=fake_gh, repomix=fake_repomix)
    r.refresh(); rep = r.refresh()
    assert rep.ok and rep.clone_age_s < 5

def test_map_leaves_out_tests_and_stays_orientation_sized():
    from yosnoop.refresher import IGNORE, INCLUDE, REPOMIX
    assert "**/__tests__/**" in IGNORE and "**/*.test.*" in IGNORE
    assert "scripts/" not in INCLUDE and REPOMIX == "repomix@1.18.1"


def test_old_open_prs_are_kept_alongside_recent_ones(tmp_path):
    def gh(args):
        if args[0] == "pr" and "open" in args:
            return json.dumps([{"number": 3, "title": "old open", "state": "OPEN"}])
        if args[0] == "pr":
            return json.dumps([{"number": 9, "title": "new merged", "state": "MERGED"}])
        return "[]"
    Refresher(make_origin(tmp_path), tmp_path / "k", gh=gh, repomix=fake_repomix).refresh()
    st = json.loads((tmp_path / "k" / "pr-ci-status.json").read_text())
    assert [p["number"] for p in st["pull_requests"]] == [9, 3]
    assert st["counts"]["open_pull_requests"] == 1
