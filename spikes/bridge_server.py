"""Localhost websocket between the Snoop extension and Snoop's Python side.
Binds 127.0.0.1 only. First message must be a hello carrying the per-install token."""
import asyncio, hmac
from typing import Callable
from aiohttp import web, WSMsgType

CLIENTS = web.AppKey("clients", set)


def make_app(token: str, on_message: Callable[[dict], None], hello_timeout: float = 5.0) -> web.Application:
    app = web.Application()
    app[CLIENTS] = set()

    async def snoop(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        try:
            first = await asyncio.wait_for(ws.receive_json(), timeout=hello_timeout)
        except Exception:
            print("bridge: refused a connection that sent no hello"); await ws.close(code=4401, message=b"hello required"); return ws
        if first.get("type") != "hello" or not hmac.compare_digest(str(first.get("token", "")), token):
            print("bridge: refused a connection with the wrong token (re-run make_ext_config and reload the extension)")
            await ws.close(code=4401, message=b"bad token"); return ws
        await ws.send_json({"type": "ack"})
        app[CLIENTS].add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    on_message(msg.json())
        finally:
            app[CLIENTS].discard(ws)
        return ws

    app.router.add_get("/snoop", snoop)
    return app


async def broadcast(app: web.Application, message: dict) -> None:
    for ws in list(app[CLIENTS]):
        await ws.send_json(message)
