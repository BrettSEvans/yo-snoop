import re

# "Yo Snoop" (Whisper also writes you/yoh/yeah/go), or a bare "Snoop," when it drops the soft "Yo"
_WAKE = re.compile(r"^\W*(?:(yo|you|yoh|yeah|go)\W+snoop(y|s)?\b|snoopy?\s*,)", re.IGNORECASE)
_STOP = re.compile(r"\bpeanut\W*butter\b", re.IGNORECASE)

def is_wake(text: str) -> bool:
    return bool(_WAKE.search(text))

def is_stop(text: str) -> bool:
    return bool(_STOP.search(text))
