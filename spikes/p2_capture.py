"""Ask the extension for the caption region's HTML and save it to ~/.cache/snoop (never the repo).
The capture holds real names and words: build the sanitized fixture from it, then delete it (Plan 0 Task 6)."""
import asyncio, time
from pathlib import Path
from aiohttp import web
from spikes.bridge_server import make_app, broadcast
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
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    print("Listening on 127.0.0.1:8790. Speak a few lines with captions on, then press Enter to save the caption area.")
    while True:
        await asyncio.get_running_loop().run_in_executor(None, input)
        await broadcast(app, {"type": "dump"})

asyncio.run(main())
