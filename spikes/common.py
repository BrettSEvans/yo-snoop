import hashlib
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
SECRETS_DIR = pathlib.Path(__file__).parent / ".secrets"
SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
SECRETS_DIR.chmod(0o700)


def pdt_now() -> str:
    now = datetime.now(PACIFIC)
    return now.strftime("%Y-%m-%d %H:%M:%S ") + now.tzname()


def sha_prefix(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]
