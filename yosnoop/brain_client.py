import asyncio, itertools, json
from dataclasses import dataclass
from yosnoop import paths

LINE_LIMIT = 4 * 1024 * 1024  # long answers must not trip asyncio's 64 KiB readline default
MAX_RESTARTS = 1              # spec: one automatic restart, then "my brain's offline" until desk restarts


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
        self.argv, self.first, self.proc, self.ids, self.restarts = argv, first_line, None, itertools.count(1), 0

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(*self.argv, stdin=asyncio.subprocess.PIPE,
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                                                         limit=LINE_LIMIT)
        await self._send(self.first)

    async def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode()); await self.proc.stdin.drain()

    async def _reply_for(self, rid: str) -> dict:
        while True:  # skip non-JSON noise and late replies to earlier, timed-out questions
            line = await self.proc.stdout.readline()
            if not line:
                raise ConnectionError("brain exited")
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if isinstance(m, dict) and m.get("id") == rid:
                return m

    async def ask(self, question, asker, room) -> BrainReply:
        rid = str(next(self.ids))
        try:
            await self._send({"type": "ask", "id": rid, "question": question, "asker": asker, "room": room})
            m = await asyncio.wait_for(self._reply_for(rid), timeout=100)
            if m.get("type") == "answer" and isinstance(m.get("text"), str):
                return BrainReply(True, m["text"], m.get("clone_age_s", float("inf")), None)
            return BrainReply(False, "", float("inf"), m.get("reason") or "bad-reply")
        except (ConnectionError, BrokenPipeError, ConnectionResetError, asyncio.TimeoutError, ValueError):
            await self._restart()
            return BrainReply(False, "", float("inf"), "offline")

    async def _restart(self):
        if self.restarts >= MAX_RESTARTS:
            return
        self.restarts += 1
        try:
            await self.stop()
            await self.start()
        except (OSError, ConnectionError):
            pass  # the next ask reports offline

    async def stop(self):
        if not self.proc or self.proc.returncode is not None:
            return
        try:
            self.proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError):
            pass
        for signal_it in (self.proc.terminate, self.proc.kill):  # sudo forwards TERM to the brain; KILL it can't
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
                return
            except asyncio.TimeoutError:
                try:
                    signal_it()
                except ProcessLookupError:
                    return
