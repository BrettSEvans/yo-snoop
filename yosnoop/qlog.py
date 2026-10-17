import datetime, json
from pathlib import Path

FIELDS = ("ts", "asker", "room", "question", "outcome", "latency_s")


def write(entry: dict, logdir: Path, today: datetime.date | None = None) -> None:
    if set(entry) != set(FIELDS):
        raise ValueError(f"question log entries carry exactly {FIELDS}")
    logdir.mkdir(parents=True, exist_ok=True); logdir.chmod(0o700)
    with open(logdir / f"questions-{(today or datetime.date.today()).isoformat()}.ndjson", "a") as f:
        f.write(json.dumps(entry) + "\n")


def prune(logdir: Path, days: int = 7, today: datetime.date | None = None) -> None:
    cutoff = (today or datetime.date.today()) - datetime.timedelta(days=days)
    for p in logdir.glob("questions-*.ndjson"):
        try:
            if datetime.date.fromisoformat(p.stem.removeprefix("questions-")) < cutoff:
                p.unlink()
        except ValueError:
            continue
