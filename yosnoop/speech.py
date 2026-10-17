import re
from dataclasses import dataclass

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)
_MARKUP = re.compile(r"^\s*(?:[-*•]|#+|\d+[.)])\s+|[*_`]+")


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    full: str


def _speakable(s: str) -> str:
    return _MARKUP.sub("", s).strip()


def sentences(text: str) -> list[str]:
    """Split on sentence ends and on line breaks (bullets), dropping markdown so `say` never reads it."""
    parts = [p for line in text.strip().splitlines() for p in _SPLIT.split(line.strip())]
    return [c for c in (_speakable(p) for p in parts) if c]


def shape(answer: str, clone_age_s: float) -> Shaped:
    clean = _PB.sub("P B", answer)
    spoken = ["Snoop here."] + sentences(clean)[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    return Shaped(spoken, clean)
