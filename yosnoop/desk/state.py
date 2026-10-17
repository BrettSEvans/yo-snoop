import re
from dataclasses import dataclass
from yosnoop.wake import is_wake, is_stop

_WAKE_PREFIX = re.compile(r"^\W*(yo|you|yoh|yeah)\W+snoop(y|s)?\b\W*", re.IGNORECASE)


@dataclass(frozen=True)
class Ask:
    question: str


@dataclass(frozen=True)
class Stop:
    pass


def strip_wake(text: str) -> str:
    return _WAKE_PREFIX.sub("", text, count=1).strip()


class DeskState:
    def __init__(self, holdoff_s: float = 1.0):
        self.holdoff, self.muted = holdoff_s, False
        self._speaking_since, self._spoke_until = None, float("-inf")

    def speaking_started(self, t: float): self._speaking_since = t
    def speaking_ended(self, t: float): self._speaking_since, self._spoke_until = None, t

    def _blocked(self, start: float) -> bool:
        return self._speaking_since is not None or start < self._spoke_until + self.holdoff

    def on_utterance(self, text: str, start: float, end: float) -> list:
        if is_stop(text):
            self.muted = True
            return [Stop()]
        if self._blocked(start) or not is_wake(text):
            return []
        self.muted = False
        q = strip_wake(text)
        return [Ask(q)] if q else []
