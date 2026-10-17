import asyncio


class Speaker:
    def __init__(self, voice: str | None = None, runner=asyncio.create_subprocess_exec):
        self.voice, self.runner, self.proc, self._stopped = voice, runner, None, False

    async def speak(self, sentences, on_start, on_end):
        self._stopped = False
        on_start()
        try:
            for s in sentences:
                if self._stopped:
                    break
                # "--": answer text can never be read as a `say` option
                cmd = ["say", *(["-v", self.voice] if self.voice else []), "--", s]
                self.proc = await self.runner(*cmd)
                await self.proc.wait()
        finally:
            self.proc = None
            on_end()

    async def stop(self):
        self._stopped = True
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
