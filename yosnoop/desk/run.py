import asyncio, sys, time
from dataclasses import dataclass, field
from typing import Callable
from yosnoop.desk.state import Ask, Stop
from yosnoop.gate import gate, BLOCKED
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
                        await _answer(ctx, a)
                    finally:
                        ctx.inflight -= 1


async def _answer(ctx: DeskCtx, ask: Ask) -> None:
    question = ask.question
    t0 = time.monotonic()
    entry = {"ts": time.time(), "asker": ctx.host_name, "room": "desk", "question": question}
    reply = await ctx.brain.ask(question, ctx.host_name, "desk")
    on_start = lambda: ctx.state.speaking_started(time.monotonic())
    on_end = lambda: ctx.state.speaking_ended(time.monotonic())
    if ctx.state.stops != ask.stop_seq:  # "peanut butter" since this was asked: say nothing
        outcome = "stopped"
    elif not reply.ok:
        await ctx.speaker.speak(["Snoop here, my brain's offline."] if reply.reason == "offline"
                                else ["Snoop here, lost the thread, ask again."], on_start, on_end)
        outcome = "offline"
    else:
        s = shape(reply.text, reply.clone_age_s)
        # gate the raw answer and exactly what will be printed and spoken (markdown removal can rejoin a key)
        if not all(gate(t).allowed for t in (reply.text, s.full, " ".join(s.spoken))):
            await ctx.speaker.speak([BLOCKED], on_start, on_end); outcome = "blocked"
        else:
            ctx.print_fn(f"\n[Snoop → {ctx.host_name}] {s.full}")
            cut = await ctx.speaker.speak(s.spoken, on_start, on_end)
            if cut:
                ctx.print_fn("(stopped)")
            outcome = "stopped" if cut else "spoken"
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
    from yosnoop.desk.voice import make_speaker
    from yosnoop.desk.stt import Transcriber
    from yosnoop.desk.stopwatch import StopWindow, stop_watch_once, POLL_S, STOP_MODEL
    from yosnoop.prepare import prepare, ORIGIN
    from yosnoop.refresher import Refresher
    import sounddevice as sd
    import numpy as np

    dev, dry, debug = "--dev" in argv, "--dry" in argv, "--debug" in argv
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
    print("Loading speech recognition and Snoop's voice…")
    stt, stop_stt = Transcriber(), Transcriber(STOP_MODEL)
    ctx = DeskCtx(state=DeskState(), brain=brain, speaker=make_speaker(), host_name=host.display_name,
                  log=lambda e: qlog.write(e, logdir), dry=dry)
    loop, q = asyncio.get_running_loop(), asyncio.Queue()

    def on_audio(indata, frames, t, status):
        loop.call_soon_threadsafe(q.put_nowait, (indata[:, 0].copy(), time.monotonic()))

    async def refresh_loop():
        while True:
            await asyncio.sleep(REFRESH_S)
            await asyncio.to_thread(Refresher(ORIGIN, paths.knowledge_dir()).refresh)

    window = StopWindow()

    async def stop_loop():
        while True:
            await asyncio.sleep(POLL_S)
            now = time.monotonic()
            if await stop_watch_once(ctx.state, window, stop_stt.transcribe,
                                     lambda: handle_utterance(ctx, "peanut butter", now, now), now) and debug:
                print("[debug] stop phrase heard while speaking")

    tasks = set()
    refresher = None if dry else asyncio.create_task(refresh_loop())
    watcher = asyncio.create_task(stop_loop())
    ep = Endpointer()
    level = {"peak": 0.0, "at": time.monotonic()}
    if debug:
        print(f"[debug] prints mic level each second and what Whisper heard (screen only, never saved). "
              f"Speech counts above {ep.th}.")
    print(f"Snoop ({host.display_name}) is listening. Say \"Yo Snoop, …\"; \"peanut butter\" stops it; Ctrl-C quits.")
    try:
        with sd.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600, callback=on_audio):
            while True:
                frame, t = await q.get()
                window.add(frame)
                if debug:
                    level["peak"] = max(level["peak"], float(np.sqrt(np.mean(frame ** 2))))
                    if t - level["at"] >= 1.0:
                        print(f"[debug] mic level {level['peak']:.4f}  threshold {ep.threshold():.4f}" + ("  (silence: check microphone permission)"
                                                                          if level["peak"] == 0.0 else ""))
                        level.update(peak=0.0, at=t)
                u = ep.feed(frame, t)
                if u is None or ctx.state.blocked(u.start):  # overlaps Snoop's voice: only the watcher listens
                    continue
                text = await asyncio.to_thread(stt.transcribe, u.audio)
                if debug:
                    print(f"[debug] heard: {text!r}")
                task = asyncio.create_task(handle_utterance(ctx, text, u.start, u.end))
                tasks.add(task); task.add_done_callback(tasks.discard)
    finally:
        watcher.cancel()
        if refresher:
            refresher.cancel()
        await ctx.speaker.stop()
        if brain:
            await brain.stop()
