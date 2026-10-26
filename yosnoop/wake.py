import re

# "Yo Snoop" as Whisper writes it at the desk (you/yoh/yeah/yes/go, "you go/gonna Snoop"),
# or a bare "Snoop," when it drops the soft "Yo"
_WAKE = re.compile(r"^\W*(?:(yo|you|yoh|yeah|yes|go)\W+(?:(go|gonna|got)\W+)?snoop(y|s)?\b|snoopy?\s*,)",
                   re.IGNORECASE)
_STOP = re.compile(r"\bpeanut\W*butter\b", re.IGNORECASE)

def is_wake(text: str) -> bool:
    return bool(_WAKE.search(text))

def is_stop(text: str) -> bool:
    return bool(_STOP.search(text))
