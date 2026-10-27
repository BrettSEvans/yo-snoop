import asyncio, hashlib
import numpy as np
from pathlib import Path
from yosnoop.desk import voice
from yosnoop.desk.voice import KokoroSpeaker, make_speaker, files_ok, DEFAULT_VOICE

class FakePlayer:
    def __init__(self, secs=0.03): self.played, self.stopped, self.secs, self._until = [], 0, secs, 0.0
    def play(self, audio, rate):
        self.played.append(audio[0]); self._until = asyncio.get_event_loop().time() + self.secs
    def active(self): return asyncio.get_event_loop().time() < self._until
    def stop(self): self.stopped += 1; self._until = 0.0

def synth_by_index(text):  # audio whose first sample identifies the sentence
    return np.full(10, float(len(text)), np.float32)

def test_default_voice_is_onyx():
    assert DEFAULT_VOICE == "am_onyx"

def test_speaks_each_sentence_in_order():
    p, events = FakePlayer(), []
    s = KokoroSpeaker(synth=synth_by_index, player=p)
    stopped = asyncio.run(s.speak(["One.", "Three.", "Fivers."], lambda: events.append("start"), lambda: events.append("end")))
    assert p.played == [4.0, 6.0, 7.0] and events == ["start", "end"] and stopped is False

def test_stop_cuts_playback_and_skips_the_rest():
    p = FakePlayer(secs=0.2)
    s = KokoroSpeaker(synth=synth_by_index, player=p)
    async def go():
        t = asyncio.create_task(s.speak(["One.", "Two.", "Three."], lambda: None, lambda: None))
        await asyncio.sleep(0.05); await s.stop(); return await t
    assert asyncio.run(go()) is True and p.stopped >= 1 and len(p.played) == 1

def test_stop_during_synthesis_plays_nothing():
    p = FakePlayer()
    async def go():
        s = KokoroSpeaker(synth=lambda t: (__import__("time").sleep(0.1), synth_by_index(t))[1], player=p)
        t = asyncio.create_task(s.speak(["One."], lambda: None, lambda: None))
        await asyncio.sleep(0.02); await s.stop(); return await t
    assert asyncio.run(go()) is True and p.played == []

def test_files_ok_checks_presence_and_hash(tmp_path, monkeypatch):
    f = tmp_path / "a.bin"; f.write_bytes(b"x")
    monkeypatch.setattr(voice, "FILES", {"a.bin": hashlib.sha256(b"x").hexdigest()})
    assert files_ok(tmp_path)
    f.write_bytes(b"y")
    assert not files_ok(tmp_path)
    assert not files_ok(tmp_path / "missing")

def test_missing_model_falls_back_to_mac_voice(tmp_path, capsys):
    from yosnoop.desk.speak import Speaker
    s = make_speaker(tmp_path / "nope")
    assert isinstance(s, Speaker) and "./snoop voice-setup" in capsys.readouterr().out
