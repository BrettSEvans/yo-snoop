import re
from dataclasses import dataclass

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    full: str


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text.strip()) if s.strip()]


def shape(answer: str, clone_age_s: float) -> Shaped:
    clean = _PB.sub("P B", answer)
    spoken = ["Snoop here."] + sentences(clean)[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    return Shaped(spoken, clean)
