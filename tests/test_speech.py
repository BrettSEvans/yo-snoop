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
    assert shape(a, 60).spoken == ["Snoop here.", "Five PRs merged.", "None passed verify.", "PR #712 merged at 08:10 UTC."]


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
