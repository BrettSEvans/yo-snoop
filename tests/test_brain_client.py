import asyncio, sys, textwrap
from yosnoop.brain_client import BrainClient

FAKE = textwrap.dedent('''
import json, sys
cred = None
for line in sys.stdin:
    m = json.loads(line)
    if m["type"] in ("key", "dev"): cred = m["type"]; continue
    if m["type"] == "ask":
        if m["question"] == "die": sys.exit(1)
        print(json.dumps({"type": "answer", "id": m["id"], "text": f"{cred}:{m['question']}", "clone_age_s": 1.0}), flush=True)
''')

def client(tmp_path):
    f = tmp_path / "fake_brain.py"; f.write_text(FAKE)
    return BrainClient([sys.executable, str(f)], {"type": "dev"})

def test_ask_round_trip(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r = await c.ask("hello", "Brett Evans", "team"); await c.stop(); return r
    r = asyncio.run(go())
    assert r.ok and r.text == "dev:hello"

def test_dead_brain_restarts_once_then_reports_offline(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r1 = await c.ask("die", "x", "team"); r2 = await c.ask("hello", "x", "team")
        await c.stop(); return r1, r2
    r1, r2 = asyncio.run(go())
    assert not r1.ok and r1.reason == "offline" and r2.ok

def test_replies_for_other_ids_are_skipped(tmp_path):
    f = tmp_path / "late.py"
    f.write_text(textwrap.dedent('''
    import json, sys
    for line in sys.stdin:
        m = json.loads(line)
        if m["type"] == "ask":
            print(json.dumps({"type": "answer", "id": "stale", "text": "old", "clone_age_s": 1}), flush=True)
            print(json.dumps({"type": "answer", "id": m["id"], "text": "new", "clone_age_s": 1}), flush=True)
    '''))
    async def go():
        c = BrainClient([sys.executable, str(f)], {"type": "dev"}); await c.start()
        r = await c.ask("q", "x", "desk"); await c.stop(); return r
    assert asyncio.run(go()).text == "new"
