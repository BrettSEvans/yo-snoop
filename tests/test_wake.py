import pytest
from yosnoop.wake import is_wake, is_stop

@pytest.mark.parametrize("t", ["Yo Snoop, how many PRs merged?", "yo snoop what's CI",
                               "You Snoop, status?", "Yo, Snoopy, any blockers?", "  yo snoop"])
def test_wake_hits(t):
    assert is_wake(t)

@pytest.mark.parametrize("t", ["we should snoop around the logs", "yo can you snoop that",
                               "Snoop Dogg is great", "I said yo snoop earlier", "snoop"])
def test_wake_decoys(t):
    assert not is_wake(t)

@pytest.mark.parametrize("t", ["peanut butter", "Peanut butter!", "ok peanut butter please"])
def test_stop_anywhere(t):
    assert is_stop(t)

def test_stop_not_partial():
    assert not is_stop("peanut")

def test_stop_heard_as_one_word():
    assert is_stop("Peanutbutter!")

def test_whisper_hears_yo_as_go():
    assert is_wake("Go Snoop test") and is_wake("Go, Snoop, how many open PRs?")

def test_bare_snoop_with_comma_wakes_but_not_snoop_dogg():
    assert is_wake("Snoop, how many open pull requests are there?")
    assert not is_wake("Snoop Dogg had a new album out")
    assert not is_wake("we should snoop, maybe later")

def test_desk_mishearings_of_yo_snoop():
    for t in ("Yes, Snoop", "Yes Snoop, tell me", "You go Snoop", "You gonna Snoop any blockers?"):
        assert is_wake(t), t

def test_decoys_from_the_desk_run_stay_quiet():
    for t in ("Snoop around the logs later", "Yo, can you snip that branch?", "I said yo Snoop earlier but never mind",
              "Let's not Snoop on...", "Snoop", "thing is cool", "Snooping is not a feature.", "Don't snoop",
              "Snip Dogg having a new album out.", "you should snoop the logs"):
        assert not is_wake(t), t
