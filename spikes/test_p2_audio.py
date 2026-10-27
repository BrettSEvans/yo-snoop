import base64
import numpy as np
from spikes.p2_audio import decode_pcm, AudioIn


def _b64(a: np.ndarray) -> str:
    return base64.b64encode((a * 32767).astype(np.int16).tobytes()).decode()


def test_decode_round_trip():
    a = np.array([0.0, 0.5, -0.5, 0.25], np.float32)
    assert np.allclose(decode_pcm(_b64(a)), a, atol=1e-4)


def test_speech_burst_between_quiet_becomes_one_utterance():
    got = []
    ai = AudioIn(lambda u: got.append(u))
    rng = np.random.default_rng(0)
    quiet = rng.normal(0, 0.001, 16000 * 2).astype(np.float32)
    speech = (0.2 * np.sin(np.arange(16000) * 2 * np.pi * 220 / 16000)).astype(np.float32)
    t = 0.0
    for chunk in (quiet, speech, quiet):  # chunks arrive at any size; AudioIn re-frames them
        for i in range(0, chunk.size, 4096):
            part = chunk[i:i + 4096]
            ai.feed(_b64(part), t); t += part.size / 16000
    # speech ran 2.0-3.0 s; the desk endpointer keeps 0.6 s of lead-in before it
    assert len(got) == 1 and abs(got[0].start - 1.4) < 0.15 and abs(got[0].end - 3.0) < 0.15


def test_importing_the_listener_helper_does_not_start_a_server():
    import subprocess, sys
    r = subprocess.run([sys.executable, "-c", "from spikes.p2_listen import last_sentence; print('ok')"],
                       capture_output=True, text=True, timeout=10)
    assert r.stdout.strip() == "ok"
