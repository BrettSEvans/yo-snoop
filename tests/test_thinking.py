import asyncio, random
import numpy as np
from yosnoop.desk.thinking import paper_rustle, keep_company, MURMURS


def test_rustle_is_short_quiet_and_not_silent():
    a = paper_rustle(24000, random.Random(1))
    assert a.dtype == np.float32 and 0.4 <= len(a) / 24000 <= 1.0
    assert np.isfinite(a).all() and 0.02 < np.abs(a).max() <= 0.2


def test_rustles_differ():
    assert not np.array_equal(paper_rustle(24000, random.Random(1)), paper_rustle(24000, random.Random(2)))


class Spk:
    def __init__(self): self.events = []
    async def speak(self, ss, on_start, on_end):
        on_start(); self.events += ss; await asyncio.sleep(0.01); on_end(); return False
    async def play_clip(self, audio, rate, on_start, on_end):
        on_start(); self.events.append("rustle"); await asyncio.sleep(0.01); on_end(); return False


def _run(think_s, still=lambda: True):
    spk, n = Spk(), {"start": 0, "end": 0}
    async def go():
        done = asyncio.create_task(asyncio.sleep(think_s))
        await keep_company(spk, done, (0.03, 0.03), lambda: n.__setitem__("start", n["start"] + 1),
                           lambda: n.__setitem__("end", n["end"] + 1), still, random.Random(0))
        n["thinking_done"] = done.done(); done.cancel()
    asyncio.run(go())
    return spk.events, n


def test_sounds_every_few_seconds_while_thinking_with_an_occasional_murmur():
    events, n = _run(0.3)
    assert events.count("rustle") >= 3 and any(e in MURMURS for e in events)
    assert n["start"] == n["end"] == len(events) and n["thinking_done"]  # each sound counts as Snoop speaking (only a stop is heard)


def test_quick_answer_gets_no_sounds():
    assert _run(0.01)[0] == []


def test_a_stop_ends_the_sounds():
    events, _ = _run(0.3, still=lambda: False)
    assert events == []
