import asyncio, sys, time
from dataclasses import dataclass, field
from typing import Callable
from yosnoop.desk.state import Ask, Stop
from yosnoop.gate import gate
from yosnoop.speech import shape

EARSHOT = "Desk Snoop answers out loud. Use it only when everyone who can hear it is on the Saasless team."
REFRESH_S = 300


@dataclass
class DeskCtx:
    state: object
    brain: object
    speaker: object
    host_name: str
    log: Callable[[dict], None]
    print_fn: Callable[[str], None] = print
    dry: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    inflight: int = 0
    inflight_max: int = 0


async def handle_utterance(ctx: DeskCtx, text: str, start: float, end: float) -> None:
    """Callers run this as its own task per utterance, so a stop is heard while an answer is spoken."""
    for a in ctx.state.on_utterance(text, start, end):
        if isinstance(a, Stop):
            if ctx.dry:
                ctx.print_fn("[dry] STOP")
            else:
                await ctx.speaker.stop()
        elif isinstance(a, Ask):
            if ctx.dry:
                ctx.print_fn(f"[dry] WAKE: {a.question}")
            else:
                async with ctx.lock:  # one question at a time through the brain's single pipe
                    ctx.inflight += 1; ctx.inflight_max = max(ctx.inflight_max, ctx.inflight)
                    try:
                        await _answer(ctx, a.question)
                    finally:
                        ctx.inflight -= 1


async def _answer(ctx: DeskCtx, question: str) -> None:
    t0 = time.monotonic()
    entry = {"ts": time.time(), "asker": ctx.host_name, "room": "desk", "question": question}
    reply = await ctx.brain.ask(question, ctx.host_name, "desk")
    on_start = lambda: ctx.state.speaking_started(time.monotonic())
    on_end = lambda: ctx.state.speaking_ended(time.monotonic())
    if ctx.state.muted:  # "peanut butter" while the brain was thinking: say nothing
        outcome = "stopped"
    elif not reply.ok:
        await ctx.speaker.speak(["Snoop here, my brain's offline."] if reply.reason == "offline"
                                else ["Snoop here, lost the thread, ask again."], on_start, on_end)
        outcome = "offline"
    else:
        g = gate(reply.text)
        if not g.allowed:
            await ctx.speaker.speak([g.text], on_start, on_end); outcome = "blocked"
        else:
            s = shape(g.text, reply.clone_age_s)
            ctx.print_fn(f"\n[Snoop → {ctx.host_name}] {s.full}")
            await ctx.speaker.speak(s.spoken, on_start, on_end); outcome = "spoken"
    ctx.log({**entry, "outcome": outcome, "latency_s": round(time.monotonic() - t0, 2)})


def run_desk(argv: list[str]) -> int:
    try:
        return asyncio.run(_run_desk(argv))
    except KeyboardInterrupt:
        print("\nDesk Snoop stopped.")
        return 0


async def _run_desk(argv: list[str]) -> int:
    from yosnoop import hostcfg, paths, qlog
    from yosnoop.cli import ROSTER
    from yosnoop.roster import load
    from yosnoop.brain_client import BrainClient, production_argv
    from yosnoop.desk.state import DeskState
    from yosnoop.desk.endpoint import Endpointer
    from yosnoop.desk.speak import Speaker
    from yosnoop.desk.stt import Transcriber
    from yosnoop.prepare import prepare, ORIGIN
    from yosnoop.refresher import Refresher
    import sounddevice as sd

    dev, dry = "--dev" in argv, "--dry" in argv
    host = hostcfg.load_host(load(ROSTER))
    print(EARSHOT)
    logdir = paths.secrets_dir().parent / "logs"
    qlog.prune(logdir)
    brain = None
    if not dry:
        print("Preparing Snoop's notes…")
        rep = prepare(dev=dev)
        for e in rep.errors:
            print(f"  prepare: {e}")
        if dev:
            print("--dev: the brain runs as you, on your Claude login (development only).")
            brain = BrainClient([sys.executable, "-m", "yosnoop.brain_main"], {"type": "dev"})
        else:
            from yosnoop.doctor import keychain_key
            key = keychain_key()
            if key is None:
                print("No Snoop API key in your Keychain (service snoop-anthropic). See docs/RUNBOOK.md, or use --dev.")
                return 1
            brain = BrainClient(production_argv(), {"type": "key", "value": key})
            del key
        await brain.start()
    print("Loading speech recognition…")
    stt = Transcriber()
    ctx = DeskCtx(state=DeskState(), brain=brain, speaker=Speaker(), host_name=host.display_name,
                  log=lambda e: qlog.write(e, logdir), dry=dry)
    loop, q = asyncio.get_running_loop(), asyncio.Queue()

    def on_audio(indata, frames, t, status):
        loop.call_soon_threadsafe(q.put_nowait, (indata[:, 0].copy(), time.monotonic()))

    async def refresh_loop():
        while True:
            await asyncio.sleep(REFRESH_S)
            await asyncio.to_thread(Refresher(ORIGIN, paths.knowledge_dir()).refresh)

    tasks = set()
    refresher = None if dry else asyncio.create_task(refresh_loop())
    ep = Endpointer()
    print(f"Snoop ({host.display_name}) is listening. Say \"Yo Snoop, …\"; \"peanut butter\" stops it; Ctrl-C quits.")
    try:
        with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600, callback=on_audio):
            while True:
                frame, t = await q.get()
                u = ep.feed(frame, t)
                if u is None:
                    continue
                text = await asyncio.to_thread(stt.transcribe, u.audio)
                task = asyncio.create_task(handle_utterance(ctx, text, u.start, u.end))
                tasks.add(task); task.add_done_callback(tasks.discard)
    finally:
        if refresher:
            refresher.cancel()
        await ctx.speaker.stop()
        if brain:
            await brain.stop()
