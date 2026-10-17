"""One session, two questions: does context carry over, and does the cache hit?"""
import asyncio, json, tempfile, time
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage
from spikes.common import pdt_now

async def ask(client, prompt):
    t0 = time.monotonic()
    await client.query(prompt)
    text, usage = "", None
    async for msg in client.receive_response():
        if isinstance(msg, ResultMessage):
            usage = msg.usage
            text = msg.result or ""
    return text, usage, round(time.monotonic() - t0, 2)

async def main():
    with tempfile.TemporaryDirectory() as d:
        opts = ClaudeAgentOptions(allowed_tools=[], max_turns=1, cwd=d,
                                  setting_sources=[], strict_mcp_config=True,
                                  permission_mode="dontAsk",
                                  system_prompt="Answer in one short sentence.")
        async with ClaudeSDKClient(options=opts) as client:
            a1 = await ask(client, "Remember the number 4182. Reply 'ok'.")
            a2 = await ask(client, "What number did I ask you to remember?")
    print(pdt_now(), json.dumps({"q1": a1, "q2": a2}, default=str, indent=2))
    assert "4182" in a2[0], "context did not carry over"

asyncio.run(main())
