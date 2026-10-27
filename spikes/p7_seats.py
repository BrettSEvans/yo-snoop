"""P6/P7: which caption lines are Snoop's own seat, and when a second Snoop should stand down (D32)."""
import re
from spikes.roster import Roster

_SNOOP_HERE = re.compile(r"^\W*snoop\W+here\b", re.IGNORECASE)
OWN_LABEL = "You"  # Meet's caption label for the seat's own speech (P6, 2026-10-27: 165/165 lines)


def is_own_seat(speaker: str, own_label: str) -> bool:
    return speaker == own_label


def shown_as(speaker: str) -> str:
    """The name we print: the seat's own speech is Snoop, not Meet's "You"."""
    return "Snoop" if is_own_seat(speaker, OWN_LABEL) else speaker


def stand_down(my_email: str, speaker: str, text: str, roster: Roster) -> bool:
    """True when another roster member's seat says "Snoop here" and that member outranks me (lower number)."""
    if not _SNOOP_HERE.search(text):
        return False
    me = roster.by_email(my_email)
    others = roster.by_display_name(speaker)
    if me is None or len(others) != 1:
        return False
    return others[0].host_priority < me.host_priority
