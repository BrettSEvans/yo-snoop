import numpy as np
from yosnoop.desk.endpoint import Endpointer

R = 16000
def frames(level, seconds, t0):
    out, n = [], int(R * 0.1)
    for i in range(int(round(seconds / 0.1))):
        out.append((np.full(n, level, dtype=np.float32), t0 + i * 0.1))
    return out

def run(seq):
    e, got = Endpointer(), []
    for f, t in seq:
        u = e.feed(f, t)
        if u: got.append(u)
    return got

def test_speech_then_silence_yields_one_utterance():
    seq = frames(0.0, 0.5, 0) + frames(0.1, 1.0, 0.5) + frames(0.0, 1.0, 1.5)
    got = run(seq)
    assert len(got) == 1 and abs(got[0].start - 0.5) < 0.11 and got[0].audio.size >= R * 1.0

def test_short_blip_is_ignored():
    assert run(frames(0.0, 0.5, 0) + frames(0.1, 0.1, 0.5) + frames(0.0, 1.0, 0.6)) == []

def test_long_speech_is_cut_at_max():
    e = Endpointer(max_s=2.0); got = []
    for f, t in frames(0.1, 3.0, 0):
        u = e.feed(f, t)
        if u: got.append(u)
    assert len(got) == 1 and got[0].end - got[0].start <= 2.1
