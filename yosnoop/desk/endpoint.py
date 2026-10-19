from collections import deque
from dataclasses import dataclass
import numpy as np


@dataclass
class Utterance:
    start: float
    end: float
    audio: np.ndarray


class Endpointer:
    """Energy endpointer whose speech threshold rides above the room's noise floor.

    A fixed threshold failed at the desk: background sat at 0.018–0.024 RMS, above 0.015, so pauses were never
    seen. The floor is the 10th percentile of the last ~10 s of frame levels; speech must clear twice it.
    """

    WARMUP_FRAMES = 5
    FLOOR_FACTOR = 2.0
    MAX_THRESHOLD = 0.06  # a loud room never makes Snoop deaf to normal speech

    def __init__(self, rate=16000, threshold=0.015, hangover_s=0.7, min_s=0.3, max_s=20.0, history=100,
                 preroll_s=0.4):
        self.rate, self.th, self.hang, self.min, self.max = rate, threshold, hangover_s, min_s, max_s
        self._levels = deque(maxlen=history)
        self.preroll_s, self._pre = preroll_s, deque()  # quiet audio just before speech: keeps a soft first word
        self._buf, self._start, self._last_voice = [], None, None

    def threshold(self) -> float:
        floor = float(np.percentile(self._levels, 10)) if self._levels else 0.0
        return max(self.th, min(floor * self.FLOOR_FACTOR, self.MAX_THRESHOLD))

    def _emit(self, end):
        audio = np.concatenate(self._buf) if self._buf else np.zeros(0, np.float32)
        u = Utterance(self._start, end, audio)
        self._buf, self._start, self._last_voice = [], None, None
        return u if (end - u.start) >= self.min else None

    def feed(self, frame: np.ndarray, t: float):
        level = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
        self._levels.append(level)
        if len(self._levels) <= self.WARMUP_FRAMES:  # no floor yet: don't start anything
            return None
        voiced = level >= self.threshold()
        dur = frame.size / self.rate
        if self._start is None:
            if not voiced:
                self._pre.append((frame, t))
                while self._pre and t + dur - self._pre[0][1] > self.preroll_s + 1e-9:
                    self._pre.popleft()
                return None
            self._start = self._pre[0][1] if self._pre else t
            self._buf = [f for f, _ in self._pre]
            self._pre.clear()
        self._buf.append(frame)
        if voiced:
            self._last_voice = t + dur
        if t + dur - self._start >= self.max:
            return self._emit(t + dur)
        if not voiced and self._last_voice is not None and t + dur - self._last_voice >= self.hang:
            return self._emit(self._last_voice)
        return None
