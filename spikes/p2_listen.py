"""Print and log caption events from the extension with receipt time and wake/stop flags (Plan 0 Task 6).
The log holds real names and words: it lives in ~/.cache/snoop and is deleted once numbers are in findings."""
import asyncio, json, re, sys, time
from pathlib import Path
from aiohttp import web
from spikes.bridge_server import make_app, broadcast
from spikes.common import SECRETS_DIR, pdt_now
from yosnoop.wake import is_wake, is_stop
from spikes.p7_seats import shown_as

LOG = Path.home() / ".cache" / "snoop" / "p2-events.ndjson"


def last_sentence(text: str) -> str:
    """Meet keeps a speaker's turn in one block, so judge only the sentence being spoken now."""
    parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]
    return parts[-1] if parts else ""


def on_message(m):
    if m.get("type") == "dump":
        path = LOG.parent / f"snoop-caption-dom-{int(time.time())}.html"
        path.write_text(m["html"]); path.chmod(0o600)
        print(pdt_now(), "saved caption area to", path)
        return
    if m.get("type") != "caption":
        return
    now = last_sentence(m["text"])
    rec = {"recv_epoch": time.time(), "sent_epoch": m.get("ts"), "speaker": m["speaker"], "text": m["text"],
           "sentence": now, "wake": is_wake(now), "stop": is_stop(now)}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    flag = "WAKE " if rec["wake"] else "STOP " if rec["stop"] else "     "
    print(pdt_now(), flag, shown_as(m["speaker"]), "|", now[-100:])


async def main():
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    print("Listening for captions on 127.0.0.1:8790. Enter saves the caption area (for debugging); Ctrl-C quits.")
    enter = asyncio.Queue()
    asyncio.get_running_loop().add_reader(sys.stdin, lambda: (sys.stdin.readline(), enter.put_nowait(1)))
    while True:
        await enter.get()
        await broadcast(app, {"type": "dump"})

if __name__ == "__main__":  # p2_audio imports last_sentence from here
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
