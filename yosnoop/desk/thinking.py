"""Sounds while the brain looks something up, so the room knows Snoop is still there:
a paper shuffle every few seconds, and now and then a soft "hmm" in Snoop's voice.
The shuffles are generated here (no recordings, nothing to license)."""
import asyncio, random
import numpy as np

MURMURS = ("Hmm.", "Mm, okay.", "Let's see.")
GAPS_S = (4.0, 5.5, 7.0, 8.5, 10.0)  # seconds before each round of sound; the gap grows, then stays at 10 s
MURMUR_EVERY = 3     # every third sound is a murmur, the rest are paper
STILL_WORKING_S = 20.0        # still thinking after this long: say so
STILL_WORKING_EVERY_S = 30.0  # and again this often after that
STILL_WORKING = ("Still digging, this one's taking a minute.", "Still on it, hang tight.",
                 "Almost there, still looking.")


def _band(x: np.ndarray, rate: int, lo: float, hi: float) -> np.ndarray:
    """Band-pass by FFT mask with soft edges (no clicks, no ringing worth hearing)."""
    f = np.fft.rfftfreq(len(x), 1 / rate)
    m = np.clip((f - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3), 0, 1)
    return np.fft.irfft(np.fft.rfft(x) * m, len(x))


def _hump(n: int, rs) -> np.ndarray:
    """A hand moving a sheet: smooth rise and fall with a slow wobble."""
    t = np.linspace(0, 1, n)
    wobble = 1 + 0.35 * np.sin(2 * np.pi * rs.uniform(4, 9) * t + rs.uniform(0, 6.3))
    return np.sin(np.pi * t) ** rs.uniform(0.8, 2.0) * wobble


def paper_rustle(rate: int = 24000, rng: random.Random | None = None) -> np.ndarray:
    """1.2-2.0 s of handling paper, in four layers over two or three hand movements:
    a low-mid "sheet sliding" body, crackles from creases (short grains, denser when the hand moves faster),
    a little air on top, and a bass layer for the sheet's weight against the desk."""
    rng = rng or random.Random()
    rs = np.random.default_rng(rng.randrange(2**32))
    n = int(rng.uniform(1.2, 2.0) * rate)
    env = np.zeros(n)
    for _ in range(rng.randint(2, 3)):
        length = int(rng.uniform(0.35, 0.9) * rate)
        start = rng.randrange(0, max(1, n - length))
        env[start:start + length] += _hump(length, rs) * rng.uniform(0.5, 1.0)
    env /= env.max() or 1

    body = _band(rs.standard_normal(n), rate, 250, 2200) * env
    air = _band(rs.standard_normal(n), rate, 4000, 9000) * env ** 2
    bass = _band(rs.standard_normal(n), rate, 50, 280) * env  # weight of the sheet against the desk

    grains = np.zeros(n)
    for i in np.flatnonzero(rs.random(n) < env * 220 / rate):  # up to ~220 crackles a second at full movement
        g = int(rs.uniform(0.002, 0.009) * rate)
        grain = rs.standard_normal(g) * np.exp(-np.arange(g) / (g / 3)) * rs.uniform(0.2, 1.0)
        grains[i:i + g] += grain[: n - i]
    crackle = _band(grains, rate, 1200, 7000)

    def unit(x): return x / (np.abs(x).max() or 1)
    a = 0.55 * unit(body) + 0.5 * unit(crackle) + 0.12 * unit(air) + 0.21 * unit(bass)
    fade = int(0.02 * rate)
    a[:fade] *= np.linspace(0, 1, fade); a[-fade:] *= np.linspace(1, 0, fade)
    return (unit(a) * rng.uniform(0.048, 0.078)).astype(np.float32)


async def keep_company(speaker, done: asyncio.Future, gaps=GAPS_S, on_start=lambda: None, on_end=lambda: None,
                       still=lambda: True, rng: random.Random | None = None, rate: int = 24000,
                       still_working_s: float = STILL_WORKING_S,
                       still_working_every: float = STILL_WORKING_EVERY_S) -> None:
    """Until `done` finishes: a sound after each gap in `gaps` (the last gap repeats), and a spoken
    "still working" line once `still_working_s` has passed (then every `still_working_every`).
    Returns after the sound in progress ends; `still()` false (a stop was heard) ends it at once."""
    rng = rng or random.Random()
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    next_sound, next_status = t0 + gaps[0], t0 + still_working_s
    rounds = said = 0
    while True:
        await asyncio.wait({done}, timeout=max(0.0, min(next_sound, next_status) - loop.time()))
        if done.done() or not still():
            return
        now = loop.time()
        if now >= next_status:
            await speaker.speak([STILL_WORKING[said % len(STILL_WORKING)]], on_start, on_end)
            said += 1
            next_status = loop.time() + still_working_every
            next_sound = max(next_sound, loop.time() + gaps[0])  # don't rustle right after speaking
            continue
        rounds += 1
        if rounds % MURMUR_EVERY == 0:
            await speaker.speak([rng.choice(MURMURS)], on_start, on_end)
        else:
            await speaker.play_clip(paper_rustle(rate, rng), rate, on_start, on_end)
        next_sound = now + gaps[min(rounds, len(gaps) - 1)]
