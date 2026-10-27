import asyncio


class Speaker:
    def __init__(self, voice: str | None = None, runner=asyncio.create_subprocess_exec, player=None):
        self.voice, self.runner, self.proc, self._stopped = voice, runner, None, False
        self._player = player

    @property
    def player(self):  # sound effects (thinking sounds) go through sounddevice, like Snoop's own voice
        if self._player is None:
            from yosnoop.desk.voice import SoundDevicePlayer
            self._player = SoundDevicePlayer()
        return self._player

    async def play_clip(self, audio, rate, on_start, on_end) -> bool:
        from yosnoop.desk.voice import play_clip
        return await play_clip(self, audio, rate, on_start, on_end)

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
        if self._player is not None:
            self._player.stop()
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
