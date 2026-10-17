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
