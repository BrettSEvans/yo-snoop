from yosnoop.speech import sentences, shape

LONG = "One. Two is here. Three? Four! Five."

def test_sentences():
    assert sentences(LONG) == ["One.", "Two is here.", "Three?", "Four!", "Five."]

def test_long_answer_speaks_three_and_keeps_full_text():
    s = shape(LONG, 60)
    assert s.spoken == ["Snoop here.", "One.", "Two is here.", "Three?"] and s.full == LONG

def test_stale_notes_are_disclosed():
    assert shape("CI is green.", 3600).spoken[-1] == "My notes are 60 minutes old."

def test_stop_phrase_is_scrubbed():
    s = shape("Ask Jeremy about peanut butter.", 60)
    assert "peanut butter" not in " ".join(s.spoken).lower() and "peanut butter" not in s.full.lower()


def test_markdown_bullets_are_not_spoken():
    s = shape("There are 8 open PRs.\n- **#563** fixes CI.\n- #536 adds a report.", 60)
    assert s.spoken == ["Snoop here.", "There are 8 open PRs.", "#563 fixes CI.", "#536 adds a report."]


def test_identifiers_survive_and_abbreviations_do_not_split():
    s = shape("Call `snake_case_id` in __init__ now, e.g. with 2 * 3 args. Done.", 60)
    assert s.spoken == ["Snoop here.", "Call snake_case_id in __init__ now, e.g. with 2 * 3 args.", "Done."]


def test_numbered_list_marker_is_not_spoken_as_a_sentence():  # desk run 2026-10-27: third sentence was "1."
    a = "Five PRs merged. None passed verify.\n\n1. PR #712 merged at 08:10 UTC. Its verify run was cancelled.\n2. PR #711 merged."
    sp = shape(a, 60).spoken
    assert sp[:3] == ["Snoop here.", "Five PRs merged.", "None passed verify."] and len(sp) == 4
    assert sp[3].startswith("PR #712 merged at ") and sp[3].endswith(("AM.", "PM."))  # time is now in Pacific


TIERED = """Five PRs merged since yesterday. None passed verify. The newest is 712.
SUMMARY:
Five PRs merged, 708 to 712. Two verify runs failed and three were cancelled. One more merged just before yesterday.
DETAILS:
1. PR 712 narrows the seal reopen fold. Its verify run was cancelled.
2. PR 711 reopens an epic."""


def test_tiered_answer_speaks_the_lead_and_keeps_summary_and_details():
    s = shape(TIERED, 60)
    assert s.spoken == ["Snoop here.", "Five PRs merged since yesterday.", "None passed verify.", "The newest is 712."]
    assert s.summary == ["Five PRs merged, 708 to 712.", "Two verify runs failed and three were cancelled.",
                         "One more merged just before yesterday."]
    assert s.details == ["PR 712 narrows the seal reopen fold.", "Its verify run was cancelled.", "PR 711 reopens an epic."]
    assert "SUMMARY" not in s.full and "DETAILS" not in s.full and "PR 711 reopens an epic." in s.full


def test_untiered_answer_falls_back_to_the_next_sentences():
    s = shape("A. B. C. D. E. F. G. H. I.", 60)
    assert s.spoken == ["Snoop here.", "A.", "B.", "C."]
    assert s.summary == ["D.", "E.", "F.", "G.", "H."] and s.details == ["A.", "B.", "C.", "D.", "E.", "F.", "G.", "H.", "I."]


def test_markers_are_found_in_markdown_or_inline_form():
    s = shape("Lead.\n## Summary\nSum.\n**Details:** Det one. Det two.", 60)
    assert s.spoken == ["Snoop here.", "Lead."] and s.summary == ["Sum."] and s.details == ["Det one.", "Det two."]


from datetime import datetime, timezone
from yosnoop.speech import pacific

NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)  # Oct 27, 11:00 AM Pacific (daylight time)


def test_utc_times_become_pacific_12_hour():
    assert pacific("CI ran at 17:10:45Z.", NOW) == "CI ran at 10:10 AM."
    assert pacific("merged 2026-10-27 08:10 UTC.", NOW) == "merged 1:10 AM."
    assert pacific("at 2026-10-27T17:10:45Z", NOW) == "at 10:10 AM"
    assert pacific("at 2026-10-27T17:10:45.123Z", NOW) == "at 10:10 AM"


def test_other_days_keep_their_pacific_date():
    assert pacific("merged 2026-10-26 06:17 UTC", NOW) == "merged Oct 25, 11:17 PM"
    assert pacific("on 2026-12-01T20:00:00Z", NOW) == "on Dec 1, 12:00 PM"  # standard time in December: UTC-8


def test_text_without_utc_times_is_unchanged():
    for t in ("PR 712 merged.", "version 2.10.3", "ratio 3:2", "at 10:10 AM"):
        assert pacific(t, NOW) == t


def test_shape_speaks_and_prints_pacific_times():
    s = shape("The last verify run was at 17:10:45Z and failed.", 60)
    assert "Z" not in " ".join(s.spoken) and "17:10" not in s.full
