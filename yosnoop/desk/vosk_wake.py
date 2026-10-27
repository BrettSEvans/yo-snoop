"""Second wake check, side by side with Whisper: Vosk (Apache-2.0) listening only for "yo snoop"."""
import hashlib, json, shutil, urllib.request, zipfile
from pathlib import Path
import numpy as np

MODEL_NAME = "vosk-model-small-en-us-0.15"  # Apache 2.0 per alphacephei.com/vosk/models
URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
ZIP_SHA256 = "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"  # fetched 2026-10-26
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "vosk"  # git-ignored
GRAMMAR = ["yo snoop", "[unk]"]
MIN_CONF = 0.6
MAX_BEFORE_S = 0.2  # Vosk decodes a short [unk] at the start; "I said yo snoop…" puts ~0.4 s there
_MARK = ".verified"


def decide(words: list[dict], min_conf: float = MIN_CONF, max_before_s: float = MAX_BEFORE_S) -> bool:
    """Wake when "yo snoop" are the first decoded words, both confident, with little [unk] before them."""
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if a["word"] == "yo" and b["word"] == "snoop":
            before = sum(x["end"] - x["start"] for x in words[:i])
            return min(a["conf"], b["conf"]) >= min_conf and before <= max_before_s
        if a["word"] != "[unk]":
            return False
    return False


def files_ok(model_dir: Path = MODEL_DIR) -> bool:
    mark = Path(model_dir) / _MARK
    return mark.is_file() and mark.read_text().strip() == ZIP_SHA256 and (Path(model_dir) / MODEL_NAME).is_dir()


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def fetch(model_dir: Path = MODEL_DIR, download=_download) -> bool:
    """Download the 40 MB model, check its sha256, unpack it. Used by ./snoop voice-setup."""
    model_dir = Path(model_dir); model_dir.mkdir(parents=True, exist_ok=True)
    z = model_dir / f"{MODEL_NAME}.zip"
    try:
        download(URL, z)
        if hashlib.sha256(z.read_bytes()).hexdigest() != ZIP_SHA256:
            return False
        shutil.rmtree(model_dir / MODEL_NAME, ignore_errors=True)
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():  # only the model's own folder, no absolute or ../ paths
                if not n.startswith(f"{MODEL_NAME}/") or ".." in Path(n).parts:
                    return False
            zf.extractall(model_dir)
        (model_dir / _MARK).write_text(ZIP_SHA256)
        return True
    finally:
        z.unlink(missing_ok=True)


class VoskWake:
    def __init__(self, model_dir: Path = MODEL_DIR):
        from vosk import Model, SetLogLevel
        SetLogLevel(-1)
        self.model = Model(str(Path(model_dir) / MODEL_NAME))

    def check(self, audio: np.ndarray, rate: int = 16000) -> tuple[bool, str]:
        """Returns (woke, what Vosk heard) for one utterance of float32 audio."""
        from vosk import KaldiRecognizer
        r = KaldiRecognizer(self.model, rate, json.dumps(GRAMMAR))
        r.SetWords(True)
        r.AcceptWaveform((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        words = json.loads(r.FinalResult()).get("result", [])
        return decide(words), " ".join(f"{x['word']}({x['conf']:.2f})" for x in words)


def make_vosk_wake(model_dir: Path = MODEL_DIR):
    if not files_ok(model_dir):
        return None
    try:
        return VoskWake(model_dir)
    except Exception as e:
        print(f"Vosk wake check failed to load ({type(e).__name__}); showing Whisper only.")
        return None
