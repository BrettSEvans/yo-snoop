import re
from dataclasses import dataclass

BLOCKED = "Snoop here, can't share that one."
PATTERNS = {
    "anthropic-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "github-token": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"),
    "github-pat": re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "google-service-account": re.compile(r'"type"\s*:\s*"service_account"'),
    "generic-bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{30,}"),
}


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    text: str
    reason: str | None


def scan(text: str) -> list[str]:
    return [name for name, rx in PATTERNS.items() if rx.search(text)]


def gate(answer: str) -> GateResult:
    try:
        hits = scan(answer)
    except Exception:
        return GateResult(False, BLOCKED, "scanner-error")
    if hits:
        return GateResult(False, BLOCKED, "secret:" + ",".join(hits))
    return GateResult(True, answer, None)


def redact(text: str) -> str:
    """Knowledge-side scrub: replace anything key-shaped before the brain can read it."""
    for rx in PATTERNS.values():
        text = rx.sub("[REDACTED]", text)
    return text


def redact_file(path) -> bool:
    """Redact a text file in place; True if anything was replaced. Binary files are left alone."""
    from pathlib import Path
    p = Path(path)
    try:
        t = p.read_text()
    except (UnicodeDecodeError, OSError):
        return False
    r = redact(t)
    if r != t:
        p.write_text(r)
    return r != t
