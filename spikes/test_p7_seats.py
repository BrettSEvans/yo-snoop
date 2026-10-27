from spikes.p7_seats import is_own_seat, stand_down
from spikes.roster import load

R = load("config/team.json")


def test_own_seat_is_exact_label_only():
    assert is_own_seat("You", "You")
    assert not is_own_seat("Brett Evans", "You")  # the host on another device is a real participant


def test_lower_priority_snoop_stands_down():
    assert stand_down("jeremy@startup.ai", "Brett Evans", "Snoop here, CI is green", R)


def test_higher_priority_snoop_stays():
    assert not stand_down("brett@startup.ai", "Jeremy Leeds", "Snoop here, CI is green", R)


def test_ordinary_speech_never_triggers_stand_down():
    assert not stand_down("jeremy@startup.ai", "Brett Evans", "I think snoop here is fine", R)


def test_non_roster_speaker_never_triggers_stand_down():
    assert not stand_down("jeremy@startup.ai", "Some Guest", "Snoop here, hi", R)


def test_own_seat_is_shown_as_snoop():
    from spikes.p7_seats import shown_as
    assert shown_as("You") == "Snoop" and shown_as("Brett Evans") == "Brett Evans"
