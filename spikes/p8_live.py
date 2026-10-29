"""Live spike: Snoop in a Meet call end to end, reusing Desk Snoop's answer path.

Captions in (the extension), settled per sentence → DeskState (wake, armed window, stop) → the brain → the
gate and answer layers → Onyx into the meeting through the extension, with the "hold up" line and paper
shuffles while it thinks. Snoop's own captions ("You") are ignored.

NOT the Plan 4 room check (P1 is still to do). Guard for this spike: you confirm at start that only Saasless
team members (config/team.json) are in the meeting, and if a caption comes from anyone whose Meet name is not
on the roster Snoop says so once and goes quiet for the rest of the run (the label it saw is on the terminal).
A silent outsider would not be caught: that is P1.

Usage: uv run --extra desk python -m spikes.p8_live [--dev] [--debug]  (--debug prints every caption update)
"""
import asyncio, base64, re, sys, time
import numpy as np

SETTLE_S = 0.8  # Meet rewrites a caption for about a second; judge a sentence once it stops changing
GUARD_LINE = "Snoop here. Someone I don't recognize is in the meeting, so I'm going quiet for the rest of this call."
_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [p for p in _SPLIT.split(text.strip()) if p]


def guard(speaker: str, team: set, state: dict) -> str | None:
    """What Snoop says the first time a caption label is not on the team (and marks the run unsafe); else None."""
    if state["unsafe"] or speaker in team:
        return None
    state["unsafe"] = True
    return GUARD_LINE


class CaptionSettler:
    """Turns growing, self-correcting caption text into finished sentences, per caption block.

    Meet keeps one speaker's turn in one block while they talk, but in a group each turn is a new block that
    starts again at one sentence. The extension names blocks (`block`); a new block is never a rewrite of an
    old one. Without a block id the speaker's name stands in for it (solo runs, older captures)."""

    def __init__(self, settle_s: float = SETTLE_S):
        self.settle, self._cur = settle_s, {}  # key -> [sentence, changed_at, emitted, count, speaker]

    def feed(self, speaker: str, text: str, now: float, block=None) -> list[tuple[str, str]]:
        parts = _sentences(text)
        if not parts:
            return []
        key = speaker if block is None else block
        out, cur = [], self._cur.get(key)
        if cur and len(parts) > cur[3] and not cur[2]:  # a new sentence began: the previous one is finished
            out.append((speaker, parts[-2]))
            cur[2] = True
        if cur is None or cur[0] != parts[-1]:
            emitted = bool(cur and cur[2] and len(parts) == cur[3])  # same sentence, rewritten after emitting
            self._cur[key] = [parts[-1], now, emitted, len(parts), speaker]
        return out

    def tick(self, now: float) -> list[tuple[str, str]]:
        out = []
        for cur in self._cur.values():
            if not cur[2] and now - cur[1] >= self.settle:
                out.append((cur[4], cur[0])); cur[2] = True
        return out


class MeetSpeaker:
    """Desk Speaker contract (speak/stop/play_clip), but the audio goes into the meeting via the extension."""

    CHUNK_S = 1.0

    def __init__(self, send, synth, rate: int = 24000):
        self.send, self.synth, self.rate, self._stopped = send, synth, rate, False

    async def _play(self, audio: np.ndarray) -> None:
        pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
        step = int(self.rate * self.CHUNK_S) * 2
        loop = asyncio.get_running_loop()
        ends = loop.time()
        for i in range(0, len(pcm), step):
            if self._stopped:
                return
            part = pcm[i:i + step]
            await self.send({"type": "audio", "pcm_b64": base64.b64encode(part).decode(), "rate": self.rate})
            ends = max(ends, loop.time()) + len(part) / 2 / self.rate
            await asyncio.sleep(max(0.0, ends - loop.time() - 0.1))  # stay ~0.1 s ahead of playback
        while not self._stopped and loop.time() < ends:
            await asyncio.sleep(0.03)

    async def speak(self, sentences, on_start, on_end) -> bool:
        self._stopped = False
        on_start()
        try:
            for s in sentences:
                if self._stopped:
                    break
                audio = await asyncio.to_thread(self.synth, s)
                await self._play(audio)
        finally:
            on_end()
        return self._stopped

    async def play_clip(self, audio, rate, on_start, on_end) -> bool:
        self._stopped = False
        on_start()
        try:
            await self._play(audio)
        finally:
            on_end()
        return self._stopped

    async def stop(self) -> None:
        self._stopped = True
        await self.send({"type": "stop"})


async def main(argv: list[str]) -> int:
    from aiohttp import web
    from spikes.bridge_server import make_app, broadcast, CLIENTS
    from spikes.common import SECRETS_DIR, pdt_now
    from spikes.p7_seats import is_own_seat, OWN_LABEL, shown_as
    from yosnoop import hostcfg, paths, qlog
    from yosnoop.cli import ROSTER
    from yosnoop.roster import load
    from yosnoop.brain_client import BrainClient, production_argv
    from yosnoop.desk.run import DeskCtx, handle_utterance
    from yosnoop.desk.state import DeskState
    from yosnoop.desk.voice import files_ok, kokoro_synth, MODEL_DIR
    from yosnoop.prepare import prepare
    from yosnoop.wake import is_stop

    roster = load(ROSTER)
    host = hostcfg.load_host(roster)
    team = {m.display_name for m in roster.members}
    print("LIVE SPIKE, no room check yet. Snoop will answer out loud in the meeting.")
    print("Team members:", ", ".join(sorted(team)))
    if input("Is everyone in this meeting on that list? Type yes: ").strip().lower() != "yes":
        print("Not started."); return 1
    if not files_ok(MODEL_DIR):
        print("Onyx not installed: run ./snoop voice-setup"); return 1

    dev, debug = "--dev" in argv, "--debug" in argv
    print("Preparing Snoop's notes…")
    for e in (await asyncio.to_thread(prepare, dev=dev)).errors:
        print(f"  prepare: {e}")
    if dev:
        brain = BrainClient([sys.executable, "-m", "yosnoop.brain_main"], {"type": "dev"})
    else:
        from yosnoop.doctor import keychain_key
        key = keychain_key()
        if key is None:
            print("No Snoop API key in your Keychain; use --dev or see docs/RUNBOOK.md."); return 1
        brain = BrainClient(production_argv(), {"type": "key", "value": key}); del key
    await brain.start()
    print("Loading Onyx…")
    synth = await asyncio.to_thread(kokoro_synth, MODEL_DIR)

    state = {"unsafe": False}
    settler = CaptionSettler()
    stopped_sentences: set = set()
    logdir = paths.secrets_dir().parent / "logs"
    app = None

    async def send(m):
        await broadcast(app, m)

    ctx = DeskCtx(state=DeskState(interrupt_on_wake=True), brain=brain, speaker=MeetSpeaker(send, synth), host_name=host.display_name,
                  log=lambda e: qlog.write({**e, "room": "meet-spike"}, logdir))

    async def go_quiet(line: str) -> None:
        await ctx.speaker.stop()
        await ctx.speaker.speak([line], lambda: ctx.state.speaking_started(time.monotonic()),
                                lambda: ctx.state.speaking_ended(time.monotonic()))

    def judge(speaker: str, sentence: str) -> None:
        now = time.monotonic()
        print(pdt_now(), "[heard]", shown_as(speaker), "|", sentence)
        asyncio.create_task(handle_utterance(ctx, sentence, now, now, speaker=speaker))

    def on_message(m):
        if m.get("type") != "caption" or state["unsafe"]:
            return
        speaker = m["speaker"]
        if is_own_seat(speaker, OWN_LABEL):
            return  # Snoop's own speech
        line = guard(speaker, team, state)
        if line:
            print(pdt_now(), f"[guard] caption label {speaker!r} is not a team display name: Snoop is quiet for the rest of this run.")
            asyncio.create_task(go_quiet(line))
            return
        now = time.monotonic()
        last = _sentences(m["text"])[-1:] or [""]
        if debug:
            print(pdt_now(), "[caption]", shown_as(speaker), "|", m["text"][-120:])
        key = (speaker, last[0])
        if is_stop(last[0]) and key not in stopped_sentences:  # stop at once, don't wait for it to settle
            stopped_sentences.add(key)
            print(pdt_now(), "[stop]", shown_as(speaker), "|", last[0])
            asyncio.create_task(handle_utterance(ctx, "peanut butter", now, now))
        for spk, sentence in settler.feed(speaker, m["text"], now, block=m.get("block")):
            if not is_stop(sentence):
                judge(spk, sentence)

    async def ticker():
        while True:
            await asyncio.sleep(0.2)
            if not state["unsafe"]:
                for spk, sentence in settler.tick(time.monotonic()):
                    if not is_stop(sentence):
                        judge(spk, sentence)

    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    while not app[CLIENTS]:
        print(pdt_now(), "waiting for the Snoop extension (meeting open in the Snoop profile, CC on, mic unmuted)…")
        await asyncio.sleep(3)
    print(pdt_now(), 'Snoop is in the meeting. Say "Yo Snoop!", pause, then your question. "Peanut butter" stops it; so does a new "Yo Snoop". Ctrl-C quits.')
    try:
        await ticker()
    finally:
        await brain.stop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main(sys.argv[1:])))
    except KeyboardInterrupt:
        print("\nstopped")
