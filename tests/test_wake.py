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
