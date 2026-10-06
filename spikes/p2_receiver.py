"""Log Attendee webhooks with PDT receipt time. Run: uv run python -m spikes.p2_receiver"""
import json, time
from aiohttp import web
from spikes.common import pdt_now
from spikes.p2_wake import is_wake, is_stop

LOG_PATH = "/tmp/p2-events.ndjson"

def utterance_text(body: dict) -> str:
    data = body.get("data")
    if not isinstance(data, dict):
        return ""
    return (data.get("transcription") or {}).get("transcript") or ""

async def hook(req):
    body = await req.json()
    text = utterance_text(body)
    rec = {"recv_epoch": time.time(), "recv_pdt": pdt_now(), "trigger": body.get("trigger"),
           "text": text, "wake": is_wake(text), "stop": is_stop(text), "data": body.get("data")}
    with open(LOG_PATH, "a") as log:
        log.write(json.dumps(rec) + "\n")
    print(rec["recv_pdt"], rec["trigger"], f"wake={rec['wake']} stop={rec['stop']}", text[:120])
    return web.Response(text="ok")

def make_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/hook", hook)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), port=8787)
