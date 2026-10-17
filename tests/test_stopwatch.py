import asyncio
import numpy as np
from yosnoop.desk.stopwatch import StopWindow, stop_watch_once
from yosnoop.desk.state import DeskState

def test_window_keeps_only_the_last_seconds():
    w = StopWindow(rate=10, window_s=1.0)
    for i in range(5):
        w.add(np.full(4, i, np.float32))
    a = w.audio()
    assert a.size == 10 and a[-1] == 4 and a[0] == 2

def test_watch_fires_stop_while_speaking_and_clears_the_window():
    s = DeskState(); s.speaking_started(1.0)
    w = StopWindow(rate=10, window_s=1.0); w.add(np.ones(10, np.float32))
    stopped = []
    async def on_stop(): stopped.append(1)
    fired = asyncio.run(stop_watch_once(s, w, lambda a: "okay peanut butter", on_stop, now=2.0))
    assert fired and stopped == [1] and w.audio().size == 0

def test_watch_is_idle_when_not_speaking():
    s = DeskState()
    w = StopWindow(rate=10, window_s=1.0); w.add(np.ones(10, np.float32))
    called = []
    async def on_stop(): called.append(1)
    assert not asyncio.run(stop_watch_once(s, w, lambda a: called.append("t") or "peanut butter", on_stop, now=2.0))
    assert called == []

def test_utterances_that_start_while_blocked_are_not_transcribed():
    s = DeskState(); s.speaking_started(1.0); s.speaking_ended(3.0)
    assert s.blocked(2.0) and s.blocked(3.5) and not s.blocked(4.5)
