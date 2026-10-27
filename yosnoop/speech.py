import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dataclasses import dataclass, field

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*•]|#+|\d+[.)])\s+")
_PAIRED = re.compile(r"(\*\*|\*|`)(?=\S)(.+?)(?<=\S)\1")  # **bold**, *em*, `code`; never _ (identifiers) or a lone *
# The brain writes: a short spoken lead, then SUMMARY: (spoken on "the rest"), then DETAILS: (spoken on "full details")
_MARKER = re.compile(r"^\s*#*\s*\**\s*(summary|details)\s*(?:\**\s*:\s*\**|:?\s*\**\s*$)\s*(.*)$", re.IGNORECASE)
_ABBREV = re.compile(r"\b(e\.g|i\.e|vs|etc|No|approx)\.", re.IGNORECASE)


PACIFIC = ZoneInfo("America/Los_Angeles")  # PDT or PST, whichever is in effect on that date
_UTC_STAMP = re.compile(r"\b(?:(\d{4})-(\d{2})-(\d{2})[T ])?(\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?\s*(?:Z|UTC|\+00:00)(?![\w:])")


def pacific(text: str, now: datetime | None = None) -> str:
    """UTC timestamps (17:10:45Z, 2026-10-27 08:10 UTC) become Pacific 12-hour times: "10:10 AM",
    with "Oct 25," in front when it isn't today in Pacific time."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(PACIFIC).date()

    def conv(m):
        y, mo, d, hh, mm = m.groups()
        base = now.astimezone(timezone.utc) if y is None else datetime(int(y), int(mo), int(d), tzinfo=timezone.utc)
        t = base.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0).astimezone(PACIFIC)
        clock = f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"
        return clock if t.date() == today else f"{t:%b} {t.day}, {clock}"
    return _UTC_STAMP.sub(conv, text)


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
    t = _tiers(pacific(_PB.sub("P B", answer)))
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
