"""P6/P7: which caption lines are Snoop's own seat, and when a second Snoop should stand down (D32)."""
import re
from spikes.roster import Roster

_SNOOP_HERE = re.compile(r"^\W*snoop\W+here\b", re.IGNORECASE)


def is_own_seat(speaker: str, own_label: str) -> bool:
    return speaker == own_label


def stand_down(my_email: str, speaker: str, text: str, roster: Roster) -> bool:
    """True when another roster member's seat says "Snoop here" and that member outranks me (lower number)."""
    if not _SNOOP_HERE.search(text):
        return False
    me = roster.by_email(my_email)
    others = roster.by_display_name(speaker)
    if me is None or len(others) != 1:
        return False
    return others[0].host_priority < me.host_priority
