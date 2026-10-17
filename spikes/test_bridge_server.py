import asyncio
from aiohttp import WSMsgType
from aiohttp.test_utils import TestServer, TestClient
from spikes.bridge_server import make_app

TOKEN = "t-123"

async def _client(app):
    c = TestClient(TestServer(app)); await c.start_server(); return c

def test_rejects_connection_without_hello():
    async def go():
        c = await _client(make_app(TOKEN, lambda m: None, hello_timeout=0.2))
        ws = await c.ws_connect("/snoop")
        msg = await ws.receive()
        await c.close()
        return msg, ws.close_code
    msg, code = asyncio.run(go())
    assert msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING) and code == 4401

def test_rejects_wrong_token():
    async def go():
        c = await _client(make_app(TOKEN, lambda m: None))
        ws = await c.ws_connect("/snoop")
        await ws.send_json({"type": "hello", "token": "wrong"})
        await ws.receive()
        code = ws.close_code
        await c.close()
        return code
    assert asyncio.run(go()) == 4401

def test_accepts_right_token_and_forwards_messages():
    got = []
    async def go():
        c = await _client(make_app(TOKEN, got.append))
        ws = await c.ws_connect("/snoop")
        await ws.send_json({"type": "hello", "token": TOKEN})
        ack = await ws.receive_json()
        await ws.send_json({"type": "caption", "speaker": "Test A", "text": "hello", "ts": 1.0})
        await asyncio.sleep(0.05)
        await ws.close(); await c.close()
        return ack
    assert asyncio.run(go()) == {"type": "ack"}
    assert got == [{"type": "caption", "speaker": "Test A", "text": "hello", "ts": 1.0}]
