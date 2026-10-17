import asyncio, itertools, json
from dataclasses import dataclass
from yosnoop import paths


@dataclass(frozen=True)
class BrainReply:
    ok: bool
    text: str
    clone_age_s: float
    reason: str | None


def production_argv() -> list[str]:
    return ["sudo", "-n", "-u", "snoop", str(paths.bin_dir() / "brain")]


class BrainClient:
    def __init__(self, argv, first_line: dict):
        self.argv, self.first, self.proc, self.ids = argv, first_line, None, itertools.count(1)

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(*self.argv, stdin=asyncio.subprocess.PIPE,
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        await self._send(self.first)

    async def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode()); await self.proc.stdin.drain()

    async def _reply_for(self, rid: str) -> dict:
        while True:  # skip any late reply to an earlier, timed-out question
            line = await self.proc.stdout.readline()
            if not line:
                raise ConnectionError("brain exited")
            m = json.loads(line)
            if m.get("id") == rid:
                return m

    async def ask(self, question, asker, room, _retry=True) -> BrainReply:
        rid = str(next(self.ids))
        try:
            await self._send({"type": "ask", "id": rid, "question": question, "asker": asker, "room": room})
            m = await asyncio.wait_for(self._reply_for(rid), timeout=100)
            if m["type"] == "answer":
                return BrainReply(True, m["text"], m.get("clone_age_s", float("inf")), None)
            return BrainReply(False, "", float("inf"), m.get("reason"))
        except (ConnectionError, BrokenPipeError, ConnectionResetError, asyncio.TimeoutError, ValueError):
            if _retry:
                await self.stop()
                await self.start()
            return BrainReply(False, "", float("inf"), "offline")

    async def stop(self):
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.stdin.close()
                await asyncio.wait_for(self.proc.wait(), 5)
            except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError):
                self.proc.kill()
