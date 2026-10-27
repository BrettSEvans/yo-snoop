"""Sounds while the brain looks something up, so the room knows Snoop is still there:
a paper shuffle every few seconds, and now and then a soft "hmm" in Snoop's voice.
The shuffles are generated here (no recordings, nothing to license)."""
import asyncio, random
import numpy as np

MURMURS = ("Hmm.", "Mm, okay.", "Let's see.")
GAP_S = (3.0, 5.0)  # seconds between sounds
MURMUR_EVERY = 3     # every third sound is a murmur, the rest are paper


def paper_rustle(rate: int = 24000, rng: random.Random | None = None) -> np.ndarray:
    """0.5-0.9 s of crinkling: a few bursts of bright noise with fast attacks and short decays."""
    rng = rng or random.Random()
    rs = np.random.default_rng(rng.randrange(2**32))
    n = int(rng.uniform(0.5, 0.9) * rate)
    bright = np.diff(rs.standard_normal(n + 1))  # differenced noise: paper is mostly high frequencies
    env = np.zeros(n)
    for _ in range(rng.randint(4, 7)):
        start, length = rng.randrange(0, int(n * 0.85)), int(rng.uniform(0.04, 0.15) * rate)
        burst = np.exp(-np.arange(length) / (length / 4)) * rng.uniform(0.4, 1.0)
        burst[: int(0.004 * rate)] *= np.linspace(0, 1, int(0.004 * rate))
        end = min(n, start + length)
        env[start:end] += burst[: end - start]
    crackle = 0.6 + 0.4 * (rs.random(n) < 0.3)  # uneven grain, like creases
    a = bright * env * crackle
    fade = int(0.01 * rate)
    a[:fade] *= np.linspace(0, 1, fade); a[-fade:] *= np.linspace(1, 0, fade)
    return (a / (np.abs(a).max() or 1) * rng.uniform(0.08, 0.14)).astype(np.float32)


async def keep_company(speaker, done: asyncio.Future, gap=GAP_S, on_start=lambda: None, on_end=lambda: None,
                       still=lambda: True, rng: random.Random | None = None, rate: int = 24000) -> None:
    """Until `done` finishes: wait a few seconds, then make one sound. Returns after the sound in progress ends.
    `still()` false (a stop was heard) ends it at once."""
    rng = rng or random.Random()
    count = 0
    while True:
        await asyncio.wait({done}, timeout=rng.uniform(*gap))
        if done.done() or not still():
            return
        count += 1
        if count % MURMUR_EVERY == 0:
            await speaker.speak([rng.choice(MURMURS)], on_start, on_end)
        else:
            await speaker.play_clip(paper_rustle(rate, rng), rate, on_start, on_end)
