import re

# How Whisper writes "Yo Snoop" at the desk (two script reads, 2026-10-26). Lexical patching is a stopgap; a trained
# wake-word detector replaces it (see the wake-word plan).
_LEAD = r"(?:yo|you|yoh|yeah|yes|go|no)"            # "Yo" as heard
_FILLER = r"(?:go|gonna|got|have|don't|do)"          # words Whisper inserts: "You have Snoop", "You don't snoop"
_ASKS = r"(?:what|what's|who|who's|how|is|are|did|does|do|would|which|where|when|why|can|list|summarize|tell|any)"
WAKE_SRC = (rf"^\W*(?:{_LEAD}\W+(?:{_FILLER}\W+)?snoop(?:y|s|ed)?\b"   # "Yo Snoop", "You have snooped"
            rf"|snoopy?\s*,"                                           # bare "Snoop," (soft "Yo" dropped)
            rf"|snoopy?\W+(?={_ASKS}\b))")                             # bare "Snoop would…", "Snoop, what…"
_WAKE = re.compile(WAKE_SRC, re.IGNORECASE)
_STOP = re.compile(r"\bpeanut\W*butter\b", re.IGNORECASE)

def is_wake(text: str) -> bool:
    return bool(_WAKE.search(text))

def is_stop(text: str) -> bool:
    return bool(_STOP.search(text))
