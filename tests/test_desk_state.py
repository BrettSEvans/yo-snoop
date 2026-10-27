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

def test_bare_snoop_comma_is_stripped():
    assert DeskState().on_utterance("Snoop, how many open PRs?", 1.0, 2.0) == [Ask("how many open PRs?")]

def test_wake_then_pause_takes_the_next_utterance_as_the_question():
    s = DeskState()
    assert s.on_utterance("Yo Snoop", 1.0, 1.6) == []
    assert s.on_utterance("Did the verify recipe pass?", 2.4, 4.0) == [Ask("Did the verify recipe pass?")]
    assert s.on_utterance("and something else", 4.5, 5.0) == []      # armed only once

def test_armed_wake_expires():
    s = DeskState()
    s.on_utterance("Yes, Snoop", 1.0, 1.5)
    assert s.on_utterance("what is D17?", 8.0, 9.0) == []

def test_armed_wake_still_honors_stop():
    s = DeskState(); s.on_utterance("Yo Snoop", 1.0, 1.5)
    assert s.on_utterance("peanut butter", 2.0, 2.5) == [Stop()]
    assert s.on_utterance("anything", 3.0, 3.5) == []

def test_filler_and_bare_forms_strip_to_the_question():
    assert strip_wake("You have Snoop, which stage is it at?") == "which stage is it at?"
    assert strip_wake("You have snooped the verify recipe pass.") == "the verify recipe pass."
    assert strip_wake("Snoop would change in the registry MCP this week.") == "would change in the registry MCP this week."


# Vosk heard "yo snoop" where Whisper's words don't match the wake patterns (desk read 4, 2026-10-27)
def test_vosk_wake_asks_with_whisper_mishearing_stripped():
    assert DeskState().on_utterance("Your Snoop is the build passing", 1.0, 2.0, heard_wake=True) == [Ask("is the build passing")]
    assert DeskState().on_utterance("You have snipped any failing checks?", 1.0, 2.0, heard_wake=True) == [Ask("any failing checks?")]


def test_vosk_wake_without_a_snoop_word_keeps_the_whole_question():
    assert DeskState().on_utterance("is the build passing", 1.0, 2.0, heard_wake=True) == [Ask("is the build passing")]


def test_vosk_wake_on_a_bare_wake_arms_for_the_question():
    s = DeskState()
    assert s.on_utterance("You know Snoop", 1.0, 1.5, heard_wake=True) == []
    assert s.on_utterance("what is beast mode?", 2.5, 4.0) == [Ask("what is beast mode?")]


def test_vosk_wake_still_respects_holdoff_and_stop():
    s = DeskState(); s.speaking_started(10.0)
    assert s.on_utterance("Yo Snoop, CI?", 10.2, 11.0, heard_wake=True) == []
    assert s.on_utterance("You want Snoop peanut butter?", 10.5, 11.0, heard_wake=True) == [Stop()]


def test_no_vosk_wake_changes_nothing():
    assert DeskState().on_utterance("Your Snoop is the build passing", 1.0, 2.0) == []
