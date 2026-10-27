import asyncio
import numpy as np
from spikes.p8_live import CaptionSettler, MeetSpeaker


def test_sentence_settles_after_it_stops_changing():
    s = CaptionSettler(settle_s=0.8)
    assert s.feed("Brett Evans", "Yo", 0.0) == []
    assert s.feed("Brett Evans", "Yo Snoop!", 0.3) == []
    assert s.tick(0.9) == []                                # changed at 0.3: not settled yet
    assert s.tick(1.2) == [("Brett Evans", "Yo Snoop!")]
    assert s.tick(3.0) == []                                # emitted once


def test_a_new_sentence_finishes_the_previous_one_at_once():
    s = CaptionSettler()
    s.feed("Brett Evans", "Yo Snoop!", 0.0)
    assert s.feed("Brett Evans", "Yo Snoop! Is", 0.2) == [("Brett Evans", "Yo Snoop!")]
    s.feed("Brett Evans", "Yo Snoop! Is CI green?", 0.5)
    assert s.tick(1.4) == [("Brett Evans", "Is CI green?")]


def test_speakers_are_tracked_separately():
    s = CaptionSettler()
    s.feed("A", "one.", 0.0); s.feed("B", "two.", 0.5)
    assert s.tick(0.9) == [("A", "one.")] and s.tick(1.4) == [("B", "two.")]


def _speaker(sent, secs=0.1):
    async def send(m): sent.append(m)
    return MeetSpeaker(send, synth=lambda text: np.zeros(int(24000 * secs), np.float32), rate=24000)


def test_speaker_sends_audio_and_counts_as_speaking():
    sent, ev = [], []
    stopped = asyncio.run(_speaker(sent).speak(["One.", "Two."], lambda: ev.append("on"), lambda: ev.append("off")))
    assert [m["type"] for m in sent] == ["audio", "audio"] and ev == ["on", "off"] and stopped is False


def test_stop_cuts_speech_and_tells_the_page():
    sent = []
    spk = _speaker(sent, secs=3.0)
    async def go():
        t = asyncio.create_task(spk.speak(["Long."], lambda: None, lambda: None))
        await asyncio.sleep(0.2); await spk.stop(); return await t
    assert asyncio.run(go()) is True and sent[-1] == {"type": "stop"} and len([m for m in sent if m["type"] == "audio"]) == 1
