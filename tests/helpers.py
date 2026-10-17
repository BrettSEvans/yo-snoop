import subprocess, tempfile, wave
import numpy as np

def say_to_array(text: str, rate: int = 16000) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        out = f"{d}/s.wav"
        subprocess.run(["say", "-o", out, f"--data-format=LEI16@{rate}", "--file-format=WAVE", text], check=True)
        with wave.open(out) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
