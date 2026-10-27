import asyncio, random
import numpy as np
from yosnoop.desk.thinking import paper_rustle, keep_company, MURMURS, STILL_WORKING, GAPS_S, STILL_WORKING_S


def test_rustle_is_short_quiet_and_not_silent():
    a = paper_rustle(24000, random.Random(1))
    assert a.dtype == np.float32 and 1.2 <= len(a) / 24000 <= 2.0
    assert np.isfinite(a).all() and 0.02 < np.abs(a).max() <= 0.08  # 40% under the first version's 0.13


def test_rustles_differ():
    assert not np.array_equal(paper_rustle(24000, random.Random(1)), paper_rustle(24000, random.Random(2)))


def test_defaults_space_sounds_4_to_10_s_and_speak_up_at_20_s():
    assert GAPS_S[0] == 4 and GAPS_S[-1] == 10 and list(GAPS_S) == sorted(GAPS_S) and STILL_WORKING_S == 20


class Spk:
    def __init__(self): self.events, self.times = [], []
    async def speak(self, ss, on_start, on_end):
        on_start(); self.events += ss; self.times.append(asyncio.get_running_loop().time())
        await asyncio.sleep(0.005); on_end(); return False
    async def play_clip(self, audio, rate, on_start, on_end):
        on_start(); self.events.append("rustle"); self.times.append(asyncio.get_running_loop().time())
        await asyncio.sleep(0.005); on_end(); return False


def _run(think_s, still=lambda: True, gaps=(0.03,), status_s=10.0, status_every=10.0):
    spk, n = Spk(), {"start": 0, "end": 0}
    async def go():
        done = asyncio.create_task(asyncio.sleep(think_s))
        await keep_company(spk, done, gaps, lambda: n.__setitem__("start", n["start"] + 1),
                           lambda: n.__setitem__("end", n["end"] + 1), still, random.Random(0),
                           still_working_s=status_s, still_working_every=status_every)
        n["thinking_done"] = done.done(); done.cancel()
    asyncio.run(go())
    return spk, n


def test_sounds_while_thinking_with_an_occasional_murmur():
    spk, n = _run(0.3)
    assert spk.events.count("rustle") >= 3 and any(e in MURMURS for e in spk.events)
    assert n["start"] == n["end"] == len(spk.events) and n["thinking_done"]  # each sound counts as Snoop speaking


def test_gaps_grow_each_round_then_hold():
    spk, _ = _run(0.5, gaps=(0.04, 0.08, 0.12))
    d = np.diff(spk.times)
    assert len(d) >= 3 and d[0] < d[1] < d[2] and abs(d[-1] - d[-2]) < 0.04


def test_says_it_is_still_working_after_a_while():
    spk, _ = _run(0.35, gaps=(1.0,), status_s=0.1, status_every=0.15)
    said = [e for e in spk.events if e in STILL_WORKING]
    assert len(said) == 2 and said[0] != said[1]


def test_quick_answer_gets_no_sounds():
    assert _run(0.01)[0].events == []


def test_a_stop_ends_the_sounds():
    assert _run(0.3, still=lambda: False)[0].events == []
