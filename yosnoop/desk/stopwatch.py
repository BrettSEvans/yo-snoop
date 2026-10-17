"""Hear "peanut butter" while Snoop is talking: the endpointer can't cut speech that overlaps Snoop's voice."""
import asyncio
from collections import deque
import numpy as np
from yosnoop.wake import is_stop

POLL_S = 0.25
# Over Snoop's own voice Whisper hears "Do not bother"; biasing toward the phrase recovers it (0 false stops measured)
STOP_HOTWORDS = "peanut butter"
# Own small model: measured (say voices, phrase over Snoop's voice) tiny.en caught 5/6, mostly 0.2–0.6 s after the
# phrase, 0/15 false stops; base.en and small.en were slower (~2 s) and missed more.
STOP_MODEL = "tiny.en"


class StopWindow:
    def __init__(self, rate: int = 16000, window_s: float = 1.5):
        self.limit, self._frames, self._n = int(rate * window_s), deque(), 0

    def add(self, frame: np.ndarray) -> None:
        self._frames.append(frame); self._n += frame.size
        while self._frames and self._n - self._frames[0].size >= self.limit:
            self._n -= self._frames.popleft().size

    def audio(self) -> np.ndarray:
        a = np.concatenate(self._frames) if self._frames else np.zeros(0, np.float32)
        return a[-self.limit:]

    def clear(self) -> None:
        self._frames.clear(); self._n = 0


async def stop_watch_once(state, window: StopWindow, transcribe, on_stop, now: float) -> bool:
    if not state.speaking:
        return False
    audio = window.audio()
    if audio.size == 0:
        return False
    text = await asyncio.to_thread(transcribe, audio, hotwords=STOP_HOTWORDS)
    if is_stop(text):
        window.clear()
        await on_stop()
        return True
    return False
