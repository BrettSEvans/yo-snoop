import asyncio


class Speaker:
    def __init__(self, voice: str | None = None, runner=asyncio.create_subprocess_exec):
        self.voice, self.runner, self.proc, self._stopped = voice, runner, None, False

    async def speak(self, sentences, on_start, on_end) -> bool:
        """Returns True if stop() cut the answer short."""
        self._stopped = False
        on_start()
        try:
            for s in sentences:
                if self._stopped:
                    break
                # "--": answer text can never be read as a `say` option
                cmd = ["say", *(["-v", self.voice] if self.voice else []), "--", s]
                self.proc = await self.runner(*cmd)
                if self._stopped:  # stop() landed while say was starting
                    self.proc.terminate()
                await self.proc.wait()
        finally:
            self.proc = None
            on_end()
        return self._stopped

    async def stop(self):
        self._stopped = True
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
