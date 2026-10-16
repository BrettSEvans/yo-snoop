"""The brain. Runs as `snoop` (production) or the host (--dev). JSON lines on stdin/stdout."""
import asyncio, json, sys, time
from pathlib import Path

def out(obj): sys.stdout.write(json.dumps(obj) + "\n"); sys.stdout.flush()

def selftest(paths):
    readable, unreadable = [], []
    for p in paths:
        try:
            open(p, "rb").read(1); readable.append(p)
        except OSError:
            unreadable.append(p)
    out({"readable": readable, "unreadable": unreadable})

def clone_age(k: Path) -> float:
    f = k / "refreshed-at"
    return time.time() - float(f.read_text()) if f.exists() else float("inf")

async def serve():
    from claude_agent_sdk import ClaudeSDKClient, ResultMessage
    from yosnoop.brain_opts import build_options
    from yosnoop import paths
    k = paths.knowledge_dir()
    cfg = json.loads((k / "brain-config.json").read_text()) if (k / "brain-config.json").exists() else {}
    credential, key, client = None, None, None
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        msg = json.loads(line)
        t = msg.get("type")
        if t == "key":
            credential, key = "key", msg["value"]; continue
        if t == "dev":
            credential = "dev"; continue
        if t == "end_meeting":
            if client: await client.__aexit__(None, None, None); client = None
            continue
        if t != "ask":
            continue
        if credential is None:
            out({"type": "error", "id": msg["id"], "reason": "no-credential"}); continue
        try:
            if client is None:
                client = ClaudeSDKClient(options=build_options(k, cfg.get("registry_cmd"), cfg.get("serena_cmd"),
                                                               cfg.get("model", "claude-sonnet-5-5"),
                                                               cfg.get("persona", ""), api_key=key))
                await client.__aenter__()
            await client.query(f"[{msg['asker']} asks, room={msg['room']}] {msg['question']}")
            text = ""
            async def collect():
                nonlocal text
                async for m in client.receive_response():
                    if isinstance(m, ResultMessage):
                        text = m.result or ""
            await asyncio.wait_for(collect(), timeout=90)
            out({"type": "answer", "id": msg["id"], "text": text, "clone_age_s": clone_age(k)})
        except Exception as e:
            reason = "timeout" if isinstance(e, asyncio.TimeoutError) else type(e).__name__
            out({"type": "error", "id": msg["id"], "reason": reason})
            if client:  # a half-finished turn must not bleed into the next answer
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    pass
                client = None
    if client:
        await client.__aexit__(None, None, None)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2:]); return
    asyncio.run(serve())

if __name__ == "__main__":
    main()
