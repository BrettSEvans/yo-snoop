"""P2b spike: wake and stop from the meeting's audio, words from Meet's captions.

The Snoop seat's extension streams the meeting audio it receives (16 kHz mono) over the localhost bridge.
Here the desk's endpointer cuts it into utterances; Vosk checks each for "yo snoop" and tiny.en for
"peanut butter". Captions still print, so each wake shows next to the question Meet transcribed.
Audio stays in memory and is never saved; only verdicts and caption text are printed.

Usage: uv run --extra desk python -m spikes.p2_audio
"""
import asyncio, base64, sys, time
import numpy as np
from yosnoop.desk.endpoint import Endpointer
from yosnoop.wake import is_wake, is_stop

FRAME = 1600  # 0.1 s at 16 kHz, the desk's frame size


def decode_pcm(pcm_b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(pcm_b64), np.int16).astype(np.float32) / 32768


class AudioIn:
    """Re-frames chunks of any size into 0.1 s frames for the endpointer; calls on_utterance for each one cut."""

    def __init__(self, on_utterance, rate: int = 16000):
        self.ep, self.on_utterance, self._rest, self._t = Endpointer(rate=rate), on_utterance, np.zeros(0, np.float32), None

    def feed(self, pcm_b64: str, t: float) -> None:
        a = decode_pcm(pcm_b64)
        if self._t is None:
            self._t = t
        buf = np.concatenate([self._rest, a])
        n = buf.size // FRAME * FRAME
        for i in range(0, n, FRAME):
            u = self.ep.feed(buf[i:i + FRAME], self._t)
            self._t += FRAME / 16000
            if u is not None:
                self.on_utterance(u)
        self._rest = buf[n:]


def main() -> None:
    from aiohttp import web
    from spikes.bridge_server import make_app
    from spikes.common import SECRETS_DIR, pdt_now
    from spikes.p2_listen import last_sentence
    from yosnoop.desk.vosk_wake import make_vosk_wake
    from yosnoop.desk.stt import Transcriber
    from yosnoop.desk.stopwatch import STOP_MODEL, STOP_HOTWORDS

    print("Loading Vosk and the stop model…")
    vosk = make_vosk_wake()
    if vosk is None:
        sys.exit("Vosk model missing: run ./snoop voice-setup")
    stop_stt = Transcriber(STOP_MODEL)
    utterances: asyncio.Queue = asyncio.Queue()
    chunks = {"n": 0, "peak": 0.0}

    def on_utterance(u):
        utterances.put_nowait(u)

    audio_in = AudioIn(on_utterance)

    def on_message(m):
        kind = m.get("type")
        if kind == "meet_audio":
            a = decode_pcm(m["pcm_b64"])
            chunks["n"] += 1; chunks["peak"] = max(chunks["peak"], float(np.abs(a).max(initial=0)))
            audio_in.feed(m["pcm_b64"], time.monotonic())
        elif kind == "caption":
            s = last_sentence(m["text"])
            flag = "wake " if is_wake(s) else "stop " if is_stop(s) else "     "
            print(pdt_now(), "[caption]", flag, m["speaker"], "|", s[-100:])

    async def judge():
        while True:
            u = await utterances.get()
            woke, heard = await asyncio.to_thread(vosk.check, u.audio)
            stop_text = await asyncio.to_thread(stop_stt.transcribe, u.audio, hotwords=STOP_HOTWORDS)
            stop = is_stop(stop_text)
            verdict = "STOP " if stop else "WAKE " if woke else "     "
            print(pdt_now(), "[audio]  ", verdict, f"{u.end - u.start:.1f}s  vosk: {heard}")

    async def levels():  # one line every 5 s so a silent tap is obvious
        while True:
            await asyncio.sleep(5)
            print(pdt_now(), f"[tap] {chunks['n']} chunks in 5 s, peak {chunks['peak']:.3f}"
                  + ("  (no meeting audio: reload the extension and the Meet tab)" if chunks["n"] == 0 else ""))
            chunks.update(n=0, peak=0.0)

    async def serve():
        app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
        runner = web.AppRunner(app); await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", 8790).start()
        print("Listening on 127.0.0.1:8790 for meeting audio and captions (Ctrl-C quits).")
        await asyncio.gather(judge(), levels())

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
