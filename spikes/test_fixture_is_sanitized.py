import json, pathlib


def test_fixture_contains_no_roster_names_or_emails():
    html = pathlib.Path("spikes/extension/test/fixture_captions.html").read_text()
    team = json.loads(pathlib.Path("config/team.json").read_text())
    for m in team["members"]:
        for token in [m["email"], *m["display_name"].split()]:
            assert token.lower() not in html.lower(), f"real identity in fixture: {token}"
    assert "@" not in html and "googleusercontent" not in html
