import re

_WAKE = re.compile(r"^\W*(yo|you|yoh|yeah|go)\W+snoop(y|s)?\b", re.IGNORECASE)
_STOP = re.compile(r"\bpeanut\W*butter\b", re.IGNORECASE)

def is_wake(text: str) -> bool:
    return bool(_WAKE.search(text))

def is_stop(text: str) -> bool:
    return bool(_STOP.search(text))
