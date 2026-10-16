import os
from pathlib import Path

def shared() -> Path: return Path(os.environ.get("SNOOP_SHARED", "/Users/Shared/snoop"))
def knowledge_dir() -> Path: return shared() / "knowledge"
def runtime_dir() -> Path: return shared() / "runtime"
def bin_dir() -> Path: return shared() / "bin"

def _private(*parts) -> Path:
    d = Path(os.environ["HOME"]).joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True); d.chmod(0o700)
    return d

def secrets_dir() -> Path: return _private(".config", "snoop", "secrets")
def scratch_dir() -> Path: return _private(".cache", "snoop")
