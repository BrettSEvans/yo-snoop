import re
from dataclasses import dataclass

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*•]|#+|\d+[.)])\s+")
_PAIRED = re.compile(r"(\*\*|\*|`)(?=\S)(.+?)(?<=\S)\1")  # **bold**, *em*, `code`; never _ (identifiers) or a lone *
_ABBREV = re.compile(r"\b(e\.g|i\.e|vs|etc|No|approx)\.", re.IGNORECASE)


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    full: str


def _speakable(s: str) -> str:
    s = _BULLET.sub("", s)
    while True:
        t = _PAIRED.sub(r"\2", s)
        if t == s:
            return s.strip()
        s = t


def sentences(text: str) -> list[str]:
    """Split on sentence ends and on line breaks (bullets), dropping markdown so `say` never reads it."""
    guarded = _ABBREV.sub(lambda m: m.group(1) + "\x00", text.strip())  # "e.g." doesn't end a sentence
    parts = [p.replace("\x00", ".") for line in guarded.splitlines() for p in _SPLIT.split(line.strip())]
    return [c for c in (_speakable(p) for p in parts) if c]


def shape(answer: str, clone_age_s: float) -> Shaped:
    clean = _PB.sub("P B", answer)
    spoken = ["Snoop here."] + sentences(clean)[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    return Shaped(spoken, clean)
