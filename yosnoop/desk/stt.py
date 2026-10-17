import numpy as np


# Biases Whisper toward the wake word: synthetic 30-line script went 14/19 and 7/19 → 19/19 (both voices), 0 decoys
HOTWORDS = "Snoop"


class Transcriber:
    def __init__(self, model: str = "small.en", compute_type: str = "int8"):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(model, device="cpu", compute_type=compute_type)

    def transcribe(self, audio: np.ndarray, rate: int = 16000) -> str:
        assert rate == 16000, "faster-whisper expects 16 kHz mono"
        segments, _ = self.m.transcribe(audio.astype(np.float32), language="en", beam_size=1, vad_filter=False,
                                       hotwords=HOTWORDS)
        return " ".join(s.text.strip() for s in segments).strip()
