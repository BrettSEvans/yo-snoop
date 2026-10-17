import json, pytest
from spikes.roster import load

def write(tmp_path, members, domain="startup.ai"):
    p = tmp_path / "team.json"
    p.write_text(json.dumps({"domain": domain, "google_group": "snoop-team@startup.ai", "members": members}))
    return p

def m(email, name, prio):
    return {"email": email, "display_name": name, "host_priority": prio, "may_host": True, "mixed_room_asker": True}

def test_repo_roster_loads():
    r = load("config/team.json")
    assert [x.email for x in r.members] == ["brett@startup.ai", "jeremy@startup.ai", "lindsay@startup.ai"]
    assert r.by_email("jeremy@startup.ai").display_name == "Jeremy Leeds"

def test_rejects_outside_domain(tmp_path):
    with pytest.raises(ValueError, match="domain"):
        load(write(tmp_path, [m("x@gmail.com", "X", 1)]))

def test_rejects_duplicate_email(tmp_path):
    with pytest.raises(ValueError, match="duplicate email"):
        load(write(tmp_path, [m("a@startup.ai", "A", 1), m("a@startup.ai", "B", 2)]))

def test_rejects_duplicate_priority(tmp_path):
    with pytest.raises(ValueError, match="duplicate host_priority"):
        load(write(tmp_path, [m("a@startup.ai", "A", 1), m("b@startup.ai", "B", 1)]))

def test_rejects_duplicate_display_name(tmp_path):
    with pytest.raises(ValueError, match="duplicate display_name"):
        load(write(tmp_path, [m("a@startup.ai", "Sam", 1), m("b@startup.ai", "Sam", 2)]))
