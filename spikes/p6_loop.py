"""P6 probe: Snoop talks into the meeting while captions are read, and a "peanut butter" caption stops it.

Prints every caption with its speaker label, so the label Meet gives Snoop's own speech shows up (P6), and
marks lines heard while Snoop was talking. Enter makes Snoop talk (the P4 Onyx paragraph); a stop caption
from anyone ends it, printing how long after the caption arrived the stop was sent. Ctrl-C quits.
Captions print to the screen only; nothing is saved.

Usage: uv run --extra desk python -m spikes.p6_loop
"""
import asyncio, base64, sys, time
from aiohttp import web
from spikes.bridge_server import make_app, broadcast, CLIENTS
from spikes.common import SECRETS_DIR, pdt_now
from spikes.p2_listen import last_sentence
from spikes.p4_media import synth_onyx, chunks
from spikes.p7_seats import shown_as
from yosnoop.wake import is_wake, is_stop


async def main() -> None:
    pcm, rate = await asyncio.to_thread(synth_onyx)
    parts = chunks(pcm, rate)
    state = {"talking": False, "stop_at": None}
    labels: dict[str, int] = {}

    def on_message(m):
        if m.get("type") != "caption":
            return
        s = last_sentence(m["text"])
        if state["talking"]:
            labels[shown_as(m["speaker"])] = labels.get(shown_as(m["speaker"]), 0) + 1
        flag = "STOP " if is_stop(s) else "wake " if is_wake(s) else "     "
        print(pdt_now(), "[talking]" if state["talking"] else "[idle]   ", flag, repr(shown_as(m["speaker"])), "|", s[-90:])
        if is_stop(s) and state["talking"] and state["stop_at"] is None:
            state["stop_at"] = time.monotonic()

    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    enter = asyncio.Queue()
    asyncio.get_running_loop().add_reader(sys.stdin, lambda: (sys.stdin.readline(), enter.put_nowait(1)))
    while not app[CLIENTS]:
        print(pdt_now(), "waiting for the Snoop extension (open the meeting in the Snoop profile, CC on)…")
        await asyncio.sleep(3)
    print(pdt_now(), "extension connected. Enter = Snoop talks. Say \"peanut butter\" on the phone to stop it.")
    while True:
        await enter.get()
        labels.clear(); state.update(talking=True, stop_at=None)
        print(pdt_now(), "TALKING")
        how = "finished"
        for part in parts:
            if state["stop_at"] is not None:
                how = "caption"; break
            if not enter.empty():
                enter.get_nowait(); how = "Enter"; break
            await broadcast(app, {"type": "audio", "pcm_b64": base64.b64encode(part).decode(), "rate": rate})
            await asyncio.sleep(0.9)
        await broadcast(app, {"type": "stop"})
        state["talking"] = False
        lag = f", {time.monotonic() - state['stop_at']:.2f} s after the stop caption arrived" if how == "caption" else ""
        print(pdt_now(), f"STOPPED ({how}{lag}). Caption speakers while talking: {labels or 'none'}")
        print(pdt_now(), "Enter = talk again; Ctrl-C quits.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
