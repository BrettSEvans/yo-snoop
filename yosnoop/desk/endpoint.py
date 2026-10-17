from dataclasses import dataclass
import numpy as np


@dataclass
class Utterance:
    start: float
    end: float
    audio: np.ndarray


class Endpointer:
    def __init__(self, rate=16000, threshold=0.015, hangover_s=0.7, min_s=0.3, max_s=20.0):
        self.rate, self.th, self.hang, self.min, self.max = rate, threshold, hangover_s, min_s, max_s
        self._buf, self._start, self._last_voice = [], None, None

    def _emit(self, end):
        audio = np.concatenate(self._buf) if self._buf else np.zeros(0, np.float32)
        u = Utterance(self._start, end, audio)
        self._buf, self._start, self._last_voice = [], None, None
        return u if (end - u.start) >= self.min else None

    def feed(self, frame: np.ndarray, t: float):
        voiced = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))) >= self.th
        dur = frame.size / self.rate
        if self._start is None:
            if not voiced:
                return None
            self._start = t
        self._buf.append(frame)
        if voiced:
            self._last_voice = t + dur
        if t + dur - self._start >= self.max:
            return self._emit(t + dur)
        if not voiced and self._last_voice is not None and t + dur - self._last_voice >= self.hang:
            return self._emit(self._last_voice)
        return None
