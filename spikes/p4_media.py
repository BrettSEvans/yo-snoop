"""P4 probe: Snoop's Onyx voice into the meeting through the extension (Plan 0 Task 7, D42).

Enter starts a long test paragraph; Enter again sends stop (time printed, to measure how fast it cuts);
Ctrl-C quits. Audio is streamed in 1 s chunks, staying only ~0.1 s ahead of playback so a stop is quick.

Usage: uv run --extra desk python -m spikes.p4_media
"""
import asyncio, base64, sys, time
import numpy as np
from aiohttp import web
from spikes.bridge_server import make_app, broadcast, CLIENTS
from spikes.common import SECRETS_DIR, pdt_now

TEXT = ("Snoop here. Aight, peep this. This is a long test so we can time how fast the audio stops. "
        "Keep listening, nephew, because the stop button is coming any second now. ") * 4


def to_pcm16(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


def chunks(pcm: bytes, rate: int, seconds: float = 1.0):
    step = int(rate * seconds) * 2  # 16-bit mono
    return [pcm[i:i + step] for i in range(0, len(pcm), step)]


def synth_onyx() -> tuple[bytes, int]:
    from yosnoop.desk.voice import files_ok, kokoro_synth, MODEL_DIR, RATE
    if not files_ok(MODEL_DIR):
        sys.exit("Onyx voice not installed: run ./snoop voice-setup")
    print("Loading Onyx…")
    return to_pcm16(kokoro_synth(MODEL_DIR)(TEXT)), RATE


async def main() -> None:
    pcm, rate = await asyncio.to_thread(synth_onyx)
    parts = chunks(pcm, rate)
    print(f"Ready: {len(parts)} s of speech.")
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), lambda m: None)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()

    enter = asyncio.Queue()
    asyncio.get_running_loop().add_reader(sys.stdin, lambda: (sys.stdin.readline(), enter.put_nowait(1)))
    while not app[CLIENTS]:
        print(pdt_now(), "waiting for the Snoop extension (open the meeting in the Snoop profile)…")
        await asyncio.sleep(3)
    print(pdt_now(), "extension connected. Press Enter to make Snoop talk; Enter again to stop it.")
    while True:
        await enter.get()
        print(pdt_now(), "TALKING")
        stopped = False
        for part in parts:
            if not enter.empty():
                enter.get_nowait(); stopped = True
                break
            await broadcast(app, {"type": "audio", "pcm_b64": base64.b64encode(part).decode(), "rate": rate})
            await asyncio.sleep(0.9)  # ~0.1 s ahead of playback, never far ahead
        if not stopped:
            await enter.get()  # paragraph sent; wait for the stop press anyway
        await broadcast(app, {"type": "stop"})
        print(pdt_now(), f"STOP SENT at {time.time():.2f}. Enter to talk again; Ctrl-C quits.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
