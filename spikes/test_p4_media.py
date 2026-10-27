import numpy as np
from spikes.p4_media import to_pcm16, chunks


def test_pcm16_clips_and_scales():
    b = to_pcm16(np.array([0.0, 1.0, -1.0, 2.0], np.float32))
    assert list(np.frombuffer(b, "<i2")) == [0, 32767, -32767, 32767]


def test_one_second_chunks_cover_everything():
    pcm = to_pcm16(np.zeros(24000 * 2 + 100, np.float32))
    parts = chunks(pcm, 24000)
    assert [len(p) for p in parts] == [48000, 48000, 200] and b"".join(parts) == pcm
