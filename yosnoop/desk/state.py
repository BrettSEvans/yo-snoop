import re
from dataclasses import dataclass, field
from yosnoop.wake import is_wake, is_stop, WAKE_SRC

_WAKE_PREFIX = re.compile(WAKE_SRC + r"\W*", re.IGNORECASE)
ARMED_S = 5.0  # "Yo Snoop" ... pause ... question: the next utterance within this window is the question


@dataclass(frozen=True)
class Ask:
    question: str
    stop_seq: int = field(default=0, compare=False)  # stops seen when asked; a later stop silences this answer


@dataclass(frozen=True)
class Stop:
    pass


def strip_wake(text: str) -> str:
    return _WAKE_PREFIX.sub("", text, count=1).strip()


# Vosk heard "yo snoop" but Whisper wrote something else ("Your Snoop is…", "You have snipped any…"):
# drop the opening words through the first sn…-word, if one is among the first four.
_HEARD_PREFIX = re.compile(r"^\W*(?:\S+\s+){0,3}?\S*?sn\w*\W*", re.IGNORECASE)  # "F-snip" too


def strip_heard_wake(text: str) -> str:
    return _HEARD_PREFIX.sub("", text, count=1).strip()


class DeskState:
    def __init__(self, holdoff_s: float = 1.0):
        self.holdoff, self.muted, self.stops = holdoff_s, False, 0
        self._armed_until = float("-inf")
        self._speaking_since, self._spoke_until = None, float("-inf")

    def speaking_started(self, t: float): self._speaking_since = t
    def speaking_ended(self, t: float): self._speaking_since, self._spoke_until = None, t

    @property
    def speaking(self) -> bool:
        return self._speaking_since is not None

    def blocked(self, start: float) -> bool:
        """An utterance starting now can only be a stop (Snoop is talking, or just finished)."""
        return self._speaking_since is not None or start < self._spoke_until + self.holdoff

    def on_utterance(self, text: str, start: float, end: float, heard_wake: bool = False) -> list:
        """heard_wake: the Vosk wake check heard "yo snoop" at the start of this utterance."""
        if is_stop(text):
            self.muted, self.stops, self._armed_until = True, self.stops + 1, float("-inf")
            return [Stop()]
        if self.blocked(start):
            return []
        if not is_wake(text) and not heard_wake:
            if start <= self._armed_until and text.strip():
                self._armed_until = float("-inf")
                self.muted = False
                return [Ask(text.strip(), self.stops)]
            return []
        self.muted = False
        q = strip_wake(text) if is_wake(text) else strip_heard_wake(text)
        if not q:
            self._armed_until = end + ARMED_S
            return []
        self._armed_until = float("-inf")
        return [Ask(q, self.stops)]
