"""Ask the extension for the caption region's HTML and save it to ~/.cache/snoop (never the repo).
The capture holds real names and words: build the sanitized fixture from it, then delete it (Plan 0 Task 6)."""
import asyncio, logging, time
from pathlib import Path
from aiohttp import web
from spikes.bridge_server import make_app, broadcast, CLIENTS
from spikes.common import SECRETS_DIR, pdt_now

OUT = Path.home() / ".cache" / "snoop"


def on_message(m):
    if m.get("type") == "dump":
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"snoop-caption-dom-{int(time.time())}.html"
        path.write_text(m["html"]); path.chmod(0o600)
        print(pdt_now(), "saved", path, len(m["html"]), "chars", "(NO CAPTION REGION FOUND)" if m["html"] == "NO-CAPTION-REGION" else "")
    elif m.get("type") == "hello":
        print(pdt_now(), "extension connected")


async def main():
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")  # shows each connection attempt
    runner = web.AppRunner(app, access_log_format='connection attempt: %r -> %s'); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    print("Listening on 127.0.0.1:8790. Waiting for the Snoop extension in a Meet tab…")

    async def watch():  # say when the extension connects or drops
        last = -1
        while True:
            n = len(app[CLIENTS])
            if n != last:
                print(pdt_now(), f"extension connected ({n} Meet tab)" if n else "no extension connected yet: "
                      "open the meeting in the Snoop Chrome profile, with Snoop (spike) loaded, and reload the tab")
                last = n
            await asyncio.sleep(1)
    asyncio.create_task(watch())
    print("Speak a few lines with captions (CC) on, then press Enter here to save the caption area.")
    while True:
        await asyncio.get_running_loop().run_in_executor(None, input)
        n = len(app[CLIENTS])
        print(pdt_now(), f"asking {n} Meet tab(s) for the caption area…" if n else "nothing to ask: no extension connected")
        await broadcast(app, {"type": "dump"})

asyncio.run(main())
