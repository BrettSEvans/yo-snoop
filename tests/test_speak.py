import asyncio
from yosnoop.desk.speak import Speaker

class FakeProc:
    def __init__(self, log, text): self.log, self.text, self.returncode = log, text, None
    async def wait(self):
        while self.returncode is None:
            await asyncio.sleep(0.01)
            if not hasattr(self, "_t"): self._t = 0
            self._t += 1
            if self._t >= 5: self.returncode = 0
        return self.returncode
    def terminate(self): self.log.append(("terminate", self.text)); self.returncode = -15

def test_speaks_each_sentence_in_order():
    log = []
    async def runner(*cmd, **kw): log.append(cmd[-1]); return FakeProc(log, cmd[-1])
    events = []
    asyncio.run(Speaker(runner=runner).speak(["Snoop here.", "CI is green."], lambda: events.append("start"), lambda: events.append("end")))
    assert log == ["Snoop here.", "CI is green."] and events == ["start", "end"]

def test_stop_prevents_remaining_sentences():
    log = []
    async def runner(*cmd, **kw): log.append(cmd[-1]); return FakeProc(log, cmd[-1])
    async def go():
        s = Speaker(runner=runner)
        t = asyncio.create_task(s.speak(["One.", "Two.", "Three."], lambda: None, lambda: None))
        await asyncio.sleep(0.07); await s.stop(); return await t
    assert asyncio.run(go()) is True
    assert "Three." not in log and any(e[0] == "terminate" for e in log if isinstance(e, tuple))

def test_sentence_text_is_passed_after_double_dash():
    log = []
    async def runner(*cmd, **kw): log.append(cmd); return FakeProc([], cmd[-1])
    asyncio.run(Speaker(runner=runner).speak(["-v Bad"], lambda: None, lambda: None))
    assert log[0][-2:] == ("--", "-v Bad")

def test_stop_during_say_startup_still_stops():
    log = []
    async def go():
        s = Speaker()
        async def runner(*cmd):
            await s.stop()  # stop arrives while say is starting
            p = FakeProc(log, cmd[-1]); return p
        s.runner = runner
        await s.speak(["One.", "Two."], lambda: None, lambda: None)
    asyncio.run(go())
    assert ("terminate", "One.") in log


def test_mac_voice_speaker_plays_clips_and_stop_cuts_them():
    import numpy as np
    class P:
        def __init__(self): self.on, self.stops = False, 0
        def play(self, audio, rate): self.on = True
        def active(self): return self.on
        def stop(self): self.stops += 1; self.on = False
    p = P(); s = Speaker(player=p)
    async def go():
        t = asyncio.create_task(s.play_clip(np.zeros(10, np.float32), 24000, lambda: None, lambda: None))
        await asyncio.sleep(0.05); await s.stop(); return await t
    assert asyncio.run(go()) is True and p.stops == 1
