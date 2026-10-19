from yosnoop.desk.state import DeskState, Ask, Stop, strip_wake

def test_wake_asks():
    s = DeskState()
    assert s.on_utterance("Yo Snoop, is CI green?", 1.0, 2.5) == [Ask("is CI green?")]

def test_decoy_does_nothing():
    assert DeskState().on_utterance("we should snoop around the logs", 1.0, 2.0) == []

def test_own_speech_cannot_wake():
    s = DeskState(); s.speaking_started(10.0)
    assert s.on_utterance("Yo Snoop here, three PRs merged", 10.2, 12.0) == []
    s.speaking_ended(13.0)
    assert s.on_utterance("Yo Snoop, CI?", 13.5, 14.0) == []      # starts inside the 1 s hold-off
    assert s.on_utterance("Yo Snoop, CI?", 14.5, 15.0) == [Ask("CI?")]

def test_utterance_that_began_while_speaking_cannot_wake():
    s = DeskState(); s.speaking_started(10.0); s.speaking_ended(12.0)
    assert s.on_utterance("Yo Snoop, CI?", 11.5, 14.0) == []

def test_stop_works_while_speaking_and_mutes_until_wake():
    s = DeskState(); s.speaking_started(10.0)
    assert s.on_utterance("peanut butter", 11.0, 11.5) == [Stop()]
    assert s.muted
    s.speaking_ended(11.6)
    assert s.on_utterance("Yo Snoop, CI?", 13.0, 14.0) == [Ask("CI?")]
    assert not s.muted

def test_empty_question_is_ignored():
    assert DeskState().on_utterance("Yo Snoop", 1.0, 1.5) == []

def test_strip_wake():
    assert strip_wake("Yo, Snoopy, any blockers?") == "any blockers?"

def test_go_snoop_wakes_and_is_stripped():
    assert DeskState().on_utterance("Go Snoop, how many open PRs?", 1.0, 2.0) == [Ask("how many open PRs?")]
