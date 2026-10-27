"""Snoop's voice: Kokoro (Apache-2.0, runs on the Mac) with the am_onyx voice; macOS `say` when the model is absent."""
import asyncio, hashlib
from pathlib import Path
import numpy as np

REPO = "hexgrad/Kokoro-82M"
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "kokoro"  # git-ignored: the model is too big for GitHub
DEFAULT_VOICE = "am_onyx"
RATE = 24000
FILES = {  # sha256 of the exact files fetched 2026-10-26; voice hash matches Kokoro's VOICES.md (e8452be1)
    "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
    "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    f"voices/{DEFAULT_VOICE}.pt": "e8452be16cd0f6da7b4579eaf7b1e4506e92524882053d86d72b96b9a7fed584",
}


def files_ok(model_dir: Path) -> bool:
    for name, sha in FILES.items():
        f = Path(model_dir) / name
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != sha:
            return False
    return True


def fetch(model_dir: Path = MODEL_DIR) -> bool:
    """Download the model and voice (~330 MB) and verify them. Used by ./snoop voice-setup."""
    from huggingface_hub import hf_hub_download
    for name in FILES:
        hf_hub_download(REPO, name, local_dir=str(model_dir))
    return files_ok(model_dir)


class SoundDevicePlayer:
    def play(self, audio, rate):
        import sounddevice as sd
        sd.play(audio, rate)

    def active(self) -> bool:
        import sounddevice as sd
        s = sd.get_stream()
        return bool(s and s.active)

    def stop(self):
        import sounddevice as sd
        sd.stop()


def kokoro_synth(model_dir: Path = MODEL_DIR, voice: str = DEFAULT_VOICE):
    """Load once (~8 s); returns text -> float32 audio at 24 kHz."""
    import torch
    from kokoro import KModel, KPipeline
    model = KModel(config=str(model_dir / "config.json"), model=str(model_dir / "kokoro-v1_0.pth"), repo_id=REPO).eval()
    pipe = KPipeline(lang_code="a", model=model, repo_id=REPO)
    pack = torch.load(str(model_dir / "voices" / f"{voice}.pt"), weights_only=True)

    def synth(text: str) -> np.ndarray:
        parts = [r.audio.numpy() for r in pipe(text, voice=pack) if r.audio is not None]
        return np.concatenate(parts).astype(np.float32) if parts else np.zeros(0, np.float32)
    return synth


async def play_clip(owner, audio, rate, on_start, on_end) -> bool:
    """Play a sound effect through owner.player; owner.stop() cuts it. Returns True if cut."""
    owner._stopped = False
    on_start()
    try:
        owner.player.play(audio, rate)
        while owner.player.active() and not owner._stopped:
            await asyncio.sleep(0.03)
    finally:
        on_end()
    return owner._stopped


class KokoroSpeaker:
    """Same contract as desk.speak.Speaker: speak() returns True when stop() cut it short."""

    def __init__(self, synth, player=None, poll_s: float = 0.03):
        self.synth, self.player, self.poll, self._stopped = synth, player or SoundDevicePlayer(), poll_s, False

    async def speak(self, sentences, on_start, on_end) -> bool:
        self._stopped = False
        on_start()
        try:
            for s in sentences:
                if self._stopped:
                    break
                audio = await asyncio.to_thread(self.synth, s)
                if self._stopped:
                    break
                self.player.play(audio, RATE)
                while self.player.active() and not self._stopped:
                    await asyncio.sleep(self.poll)
        finally:
            on_end()
        return self._stopped

    async def play_clip(self, audio, rate, on_start, on_end) -> bool:
        return await play_clip(self, audio, rate, on_start, on_end)

    async def stop(self):
        self._stopped = True
        self.player.stop()


def make_speaker(model_dir: Path = MODEL_DIR, voice: str = DEFAULT_VOICE):
    from yosnoop.desk.speak import Speaker
    if not files_ok(model_dir):
        print("Snoop's voice model isn't installed; using the Mac voice. Run ./snoop voice-setup to get Onyx.")
        return Speaker()
    try:
        return KokoroSpeaker(kokoro_synth(model_dir, voice))
    except Exception as e:
        print(f"Snoop's voice failed to load ({type(e).__name__}); using the Mac voice.")
        return Speaker()
