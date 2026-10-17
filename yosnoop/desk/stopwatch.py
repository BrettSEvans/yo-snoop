"""Hear "peanut butter" while Snoop is talking: the endpointer can't cut speech that overlaps Snoop's voice."""
import asyncio
from collections import deque
import numpy as np
from yosnoop.wake import is_stop

POLL_S = 0.4


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
    text = await asyncio.to_thread(transcribe, audio)
    if is_stop(text):
        window.clear()
        await on_stop()
        return True
    return False
