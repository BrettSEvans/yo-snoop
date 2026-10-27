import re
from dataclasses import dataclass, field

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*•]|#+|\d+[.)])\s+")
_PAIRED = re.compile(r"(\*\*|\*|`)(?=\S)(.+?)(?<=\S)\1")  # **bold**, *em*, `code`; never _ (identifiers) or a lone *
# The brain writes: a short spoken lead, then SUMMARY: (spoken on "the rest"), then DETAILS: (spoken on "full details")
_MARKER = re.compile(r"^\s*#*\s*\**\s*(summary|details)\s*(?:\**\s*:\s*\**|:?\s*\**\s*$)\s*(.*)$", re.IGNORECASE)
_ABBREV = re.compile(r"\b(e\.g|i\.e|vs|etc|No|approx)\.", re.IGNORECASE)


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    full: str
    summary: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


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
    # drop list markers before splitting, or "1. PR #712 …" splits into a sentence "1."
    parts = [p.replace("\x00", ".") for line in guarded.splitlines()
             for p in _SPLIT.split(_BULLET.sub("", line).strip())]
    return [c for c in (_speakable(p) for p in parts) if c]


def _tiers(text: str) -> dict[str, str]:
    parts, cur = {"lead": [], "summary": [], "details": []}, "lead"
    for line in text.splitlines():
        m = _MARKER.match(line)
        if m:
            cur = m.group(1).lower()
            line = m.group(2) or ""
        parts[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in parts.items()}


def shape(answer: str, clone_age_s: float) -> Shaped:
    t = _tiers(_PB.sub("P B", answer))
    lead = sentences(t["lead"])
    spoken = ["Snoop here."] + lead[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    if t["summary"] or t["details"]:
        summary, details = sentences(t["summary"]), sentences(t["details"])
        summary, details = summary or details[:5], details or lead + summary
        full = "\n\n".join(x for x in (t["lead"], t["details"]) if x)
    else:  # an answer without the markers: "the rest" is the next five sentences, "full details" is all of it
        summary, details, full = lead[3:8], lead, t["lead"]
    return Shaped(spoken, full, summary, details)
