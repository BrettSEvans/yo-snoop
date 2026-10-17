"""The brain. Runs as `snoop` (production) or the host (--dev). JSON lines on stdin/stdout."""
import asyncio, json, sys, time
from pathlib import Path

def out(obj): sys.stdout.write(json.dumps(obj) + "\n"); sys.stdout.flush()

def selftest(paths):
    """Directories are probed by listing them (open() on a directory always fails, whatever its mode)."""
    import os
    readable, unreadable, missing = [], [], []
    for p in paths:
        try:
            if os.path.isdir(p):
                os.listdir(p)
            else:
                open(p, "rb").read(1)
            readable.append(p)
        except FileNotFoundError:
            missing.append(p)
        except OSError:
            unreadable.append(p)
    out({"readable": readable, "unreadable": unreadable, "missing": missing})

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
        try:
            msg = json.loads(line)
            t = msg.get("type") if isinstance(msg, dict) else None
        except ValueError:
            out({"type": "error", "id": None, "reason": "bad-json"}); continue
        if t == "key":
            credential, key = "key", msg["value"]; continue
        if t == "dev":
            credential = "dev"; continue
        if t == "end_meeting":
            if client: await client.__aexit__(None, None, None); client = None
            continue
        if t != "ask":
            continue
        if credential is None or not isinstance(msg.get("question"), str):
            out({"type": "error", "id": msg.get("id"), "reason": "no-credential" if credential is None else "bad-ask"})
            continue
        try:
            if client is None:
                client = ClaudeSDKClient(options=build_options(k, cfg.get("registry_cmd"), cfg.get("serena_cmd"),
                                                               cfg.get("model", "claude-sonnet-5-5"),
                                                               cfg.get("persona", ""), api_key=key))
                await client.__aenter__()
            await client.query(f"[{msg.get('asker', '?')} asks, room={msg.get('room', '?')}] {msg['question']}")
            text = ""
            async def collect():
                nonlocal text
                async for m in client.receive_response():
                    if isinstance(m, ResultMessage):
                        text = m.result or ""
            await asyncio.wait_for(collect(), timeout=90)
            out({"type": "answer", "id": msg.get("id"), "text": text, "clone_age_s": clone_age(k)})
        except Exception as e:
            reason = "timeout" if isinstance(e, asyncio.TimeoutError) else type(e).__name__
            out({"type": "error", "id": msg.get("id"), "reason": reason})
            if client:  # a half-finished turn must not bleed into the next answer
                try:
                    await client.__aexit__(None, None, None)
                except Exception:
                    pass
                client = None
    if client:
        await client.__aexit__(None, None, None)

async def control():
    """One doctor turn through the production options. Reports text, error, denials and the init tool list."""
    from claude_agent_sdk import ClaudeSDKClient, ResultMessage, SystemMessage, AssistantMessage, ToolUseBlock
    from yosnoop.brain_opts import build_options, KEY_STRIP
    from yosnoop import paths
    k = paths.knowledge_dir()
    cfg = json.loads((k / "brain-config.json").read_text()) if (k / "brain-config.json").exists() else {}
    cred = json.loads(sys.stdin.readline())
    req = json.loads(sys.stdin.readline())
    key = cred.get("value") if cred.get("type") == "key" else None
    opts = build_options(k, cfg.get("registry_cmd"), cfg.get("serena_cmd"), cfg.get("model", "claude-sonnet-5-5"),
                         cfg.get("persona", ""), api_key=key)
    if req.get("envprobe"):  # C5 only: wrapped like production, or unwrapped as the negative control
        probe = [sys.executable, "-m", "yosnoop.envprobe_server"]
        cmd = [*KEY_STRIP, *probe] if req["envprobe"] == "wrapped" else probe
        opts.mcp_servers = {**opts.mcp_servers, "envprobe": {"type": "stdio", "command": cmd[0], "args": cmd[1:]}}
        opts.allowed_tools = [*opts.allowed_tools, "mcp__envprobe__env_probe"]
    res = {"type": "control_result", "text": "", "error": None, "denials": 0, "tools_seen": [], "tools_called": []}
    try:
        async with ClaudeSDKClient(options=opts) as c:
            await c.query(req["prompt"])
            async def collect():
                async for m in c.receive_response():
                    if isinstance(m, AssistantMessage):
                        res["tools_called"] += [b.name for b in m.content if isinstance(b, ToolUseBlock)]
                    if isinstance(m, SystemMessage) and m.subtype == "init":
                        res["tools_seen"] = sorted(m.data.get("tools", []))
                    if isinstance(m, ResultMessage):
                        res["text"] = m.result or ""
                        res["denials"] = len(m.permission_denials or [])
                        if m.is_error:
                            res["error"] = m.subtype or "result-error"
            await asyncio.wait_for(collect(), timeout=150)
    except Exception as e:
        res["error"] = "timeout" if isinstance(e, asyncio.TimeoutError) else type(e).__name__
    out(res)

def serena_tools():
    from yosnoop.brain_opts import KEY_STRIP
    from yosnoop.serena_cfg import list_tools, assert_tools
    from yosnoop import paths
    k = paths.knowledge_dir()
    cfg = json.loads((k / "brain-config.json").read_text()) if (k / "brain-config.json").exists() else {}
    if not cfg.get("serena_cmd"):
        out({"error": "no serena_cmd in brain-config.json"}); return
    try:
        tools = asyncio.run(list_tools([*KEY_STRIP, *cfg["serena_cmd"]]))
        assert_tools(tools)
        out({"tools": sorted(tools), "error": None})
    except Exception as e:
        out({"error": f"{type(e).__name__}: {e}"[:300]})

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2:]); return
    if len(sys.argv) > 1 and sys.argv[1] == "--control":
        asyncio.run(control()); return
    if len(sys.argv) > 1 and sys.argv[1] == "--serena-tools":
        serena_tools(); return
    asyncio.run(serve())

if __name__ == "__main__":
    main()
