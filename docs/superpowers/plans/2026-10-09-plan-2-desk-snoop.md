# Snoop Plan 2 — Desk Snoop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `./snoop desk` lets any roster member say "Yo Snoop, …" into their Mac's microphone and hear the answer from their speakers — Phase 1a (spec D33, D37). No Google, no Meet.

**Architecture:** All on the host's Mac. A microphone stream is cut into utterances by a simple energy endpointer; each utterance is transcribed on-device by `faster-whisper`; a pure desk state machine applies wake ("Yo Snoop"), mute ("peanut butter") and self-voice rules; questions go to the Plan 1 brain (as `snoop`; or `--dev` as the host); the answer passes the gate, is spoken with macOS `say` ("Snoop here." + at most 3 sentences), and is printed in full in the terminal. No audio or transcript leaves the Mac; only the question text reaches the brain.

**Tech Stack:** Python 3.12, `sounddevice`, `numpy`, `faster-whisper` (MIT; model `small.en`, int8, CPU), macOS `say`; Plan 1's `yosnoop` package.

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` — D6, D7, D11, D25, D28 (spoken label), D33, D35, D37–D39; §5.4. **Requires Plan 1 complete.**

## Global Constraints

- Desk Snoop speaks out loud in the room. On every start it prints: "Desk Snoop answers out loud. Use it only when everyone who can hear it is on the Saasless team." (The Meet version's guest checks do not exist here.)
- Every spoken answer starts "Snoop here."; at most 3 sentences are spoken; the full answer always prints in the terminal (D33).
- While Snoop is speaking, and for 1.0 s after, utterances can only trigger **stop**, never wake (D37). Answers are scrubbed of the phrase "peanut butter".
- Audio stays in memory; nothing is written to disk except the question log (`qlog`, exact fields, 7-day retention).
- The microphone permission prompt is macOS's; the runbook (Plan 3) tells the host to allow it for their terminal app.
- The Whisper model downloads once (~0.5 GB) into the host's cache; record the actual size.

## Review Focus

1. **Snoop wakes itself** — its own "Snoop here…" picked up by the mic must never start a new question. Task 3, test `test_own_speech_cannot_wake`.
2. **"Peanut butter" can't interrupt a long answer** — expected: speech stops within ~1 s of the utterance ending. Task 5, Step 4.
3. **Transcription mangles the wake phrase** — expected: ≥ 18/20 real "Yo Snoop" lines detected, 0/10 decoys. Task 6, Step 2.
4. **Question log captures room talk** — expected: only wake-phrase questions are logged. Task 4.
5. **Brain offline mid-session** — expected: "Snoop here, my brain's offline." and one automatic restart. Task 4.

---

### Task 1: Endpointer — cut the mic stream into utterances (pure)

**Files:** Create `yosnoop/desk/__init__.py`, `yosnoop/desk/endpoint.py`, `tests/test_endpoint.py`

**Interfaces:** `Endpointer(rate=16000, threshold=0.015, hangover_s=0.7, min_s=0.3, max_s=20.0)`; `feed(frame: np.ndarray, t: float) -> Utterance | None`; `Utterance(start: float, end: float, audio: np.ndarray)`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_endpoint.py
import numpy as np
from yosnoop.desk.endpoint import Endpointer

R = 16000
def frames(level, seconds, t0):
    out, n = [], int(R * 0.1)
    for i in range(int(seconds / 0.1)):
        out.append((np.full(n, level, dtype=np.float32), t0 + i * 0.1))
    return out

def run(seq):
    e, got = Endpointer(), []
    for f, t in seq:
        u = e.feed(f, t)
        if u: got.append(u)
    return got

def test_speech_then_silence_yields_one_utterance():
    seq = frames(0.0, 0.5, 0) + frames(0.1, 1.0, 0.5) + frames(0.0, 1.0, 1.5)
    got = run(seq)
    assert len(got) == 1 and abs(got[0].start - 0.5) < 0.11 and got[0].audio.size >= R * 1.0

def test_short_blip_is_ignored():
    assert run(frames(0.0, 0.5, 0) + frames(0.1, 0.1, 0.5) + frames(0.0, 1.0, 0.6)) == []

def test_long_speech_is_cut_at_max():
    e = Endpointer(max_s=2.0); got = []
    for f, t in frames(0.1, 3.0, 0):
        u = e.feed(f, t)
        if u: got.append(u)
    assert len(got) == 1 and got[0].end - got[0].start <= 2.1
```

Run: `uv run pytest tests/test_endpoint.py -q` → Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 2: Implement**

```python
# yosnoop/desk/endpoint.py
from dataclasses import dataclass
import numpy as np


@dataclass
class Utterance:
    start: float
    end: float
    audio: np.ndarray


class Endpointer:
    def __init__(self, rate=16000, threshold=0.015, hangover_s=0.7, min_s=0.3, max_s=20.0):
        self.rate, self.th, self.hang, self.min, self.max = rate, threshold, hangover_s, min_s, max_s
        self._buf, self._start, self._last_voice = [], None, None

    def _emit(self, end):
        audio = np.concatenate(self._buf) if self._buf else np.zeros(0, np.float32)
        u = Utterance(self._start, end, audio)
        self._buf, self._start, self._last_voice = [], None, None
        return u if (end - u.start) >= self.min else None

    def feed(self, frame: np.ndarray, t: float):
        voiced = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))) >= self.th
        dur = frame.size / self.rate
        if self._start is None:
            if not voiced:
                return None
            self._start = t
        self._buf.append(frame)
        if voiced:
            self._last_voice = t + dur
        if t + dur - self._start >= self.max:
            return self._emit(t + dur)
        if not voiced and self._last_voice is not None and t + dur - self._last_voice >= self.hang:
            return self._emit(self._last_voice)
        return None
```

- [ ] **Step 3: Green** — 3 PASS. **Step 4: Commit** — `git add yosnoop/desk tests/test_endpoint.py && git commit -m "desk: energy endpointer"`

---

### Task 2: Transcriber — on-device Whisper, tested with `say`-generated speech

**Files:** Create `yosnoop/desk/stt.py`, `tests/test_stt.py`, promote `spikes/p2_wake.py` → `yosnoop/wake.py` (verbatim)
**Modify:** `pyproject.toml` (`uv add faster-whisper sounddevice numpy`)

**Interfaces:** `Transcriber(model="small.en", compute_type="int8")`; `transcribe(audio: np.ndarray, rate=16000) -> str`; `say_to_array(text, rate=16000) -> np.ndarray` (test helper in `tests/helpers.py`).

- [ ] **Step 1: Failing tests** (the slow test synthesizes speech with `say`, so it needs no microphone)

```python
# tests/helpers.py
import subprocess, tempfile, wave
import numpy as np

def say_to_array(text: str, rate: int = 16000) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        out = f"{d}/s.wav"
        subprocess.run(["say", "-o", out, f"--data-format=LEI16@{rate}", "--file-format=WAVE", text], check=True)
        with wave.open(out) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
```

```python
# tests/test_stt.py
import pytest
from yosnoop.desk.stt import Transcriber
from yosnoop.wake import is_wake, is_stop
from tests.helpers import say_to_array

@pytest.fixture(scope="module")
def stt():
    return Transcriber()

@pytest.mark.slow
def test_wake_phrase_survives_transcription(stt):
    assert is_wake(stt.transcribe(say_to_array("Yo Snoop, how many pull requests merged yesterday?")))

@pytest.mark.slow
def test_stop_phrase_survives_transcription(stt):
    assert is_stop(stt.transcribe(say_to_array("Okay, peanut butter.")))

@pytest.mark.slow
def test_decoy_is_not_a_wake(stt):
    assert not is_wake(stt.transcribe(say_to_array("We should snoop around the logs later.")))
```

Register the `slow` marker in `pyproject.toml` (`markers = ["slow: needs the Whisper model"]`). Add `tests/__init__.py`.
Run: `uv run pytest tests/test_stt.py -q -m slow` → Expected: FAIL (`ModuleNotFoundError: yosnoop.desk.stt`)

- [ ] **Step 2: Implement**

```python
# yosnoop/desk/stt.py
import numpy as np


class Transcriber:
    def __init__(self, model: str = "small.en", compute_type: str = "int8"):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(model, device="cpu", compute_type=compute_type)

    def transcribe(self, audio: np.ndarray, rate: int = 16000) -> str:
        assert rate == 16000, "faster-whisper expects 16 kHz mono"
        segments, _ = self.m.transcribe(audio.astype(np.float32), language="en", beam_size=1, vad_filter=False)
        return " ".join(s.text.strip() for s in segments).strip()
```

- [ ] **Step 3: Green** — first run downloads the model; record its size (`du -sh ~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en`) and the per-utterance latency. Expected: 3 PASS. If the wake test fails because Whisper writes "Yo, Snoop" variants the regex misses, add the variant to `yosnoop/wake.py` with a new unit case in `spikes/test_p2_wake.py`'s promoted copy `tests/test_wake.py` first (RED → GREEN).
- [ ] **Step 4: Commit** — `git add yosnoop/desk/stt.py yosnoop/wake.py tests pyproject.toml uv.lock && git commit -m "desk: on-device Whisper transcriber, tested with say-generated speech"`

---

### Task 3: Desk state machine — wake, mute, never wake itself (pure)

**Files:** Create `yosnoop/desk/state.py`, `tests/test_desk_state.py`

**Interfaces:** actions `Ask(question: str)`, `Stop()`; `DeskState(holdoff_s=1.0)` with `on_utterance(text, start, end) -> list`, `speaking_started(t)`, `speaking_ended(t)`, `muted: bool`; `strip_wake(text) -> str`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_desk_state.py
from yosnoop.desk.state import DeskState, Ask, Stop, strip_wake

def test_wake_asks():
    s = DeskState()
    assert s.on_utterance("Yo Snoop, is CI green?", 1.0, 2.5) == [Ask("is CI green?")]

def test_decoy_does_nothing():
    assert DeskState().on_utterance("we should snoop around the logs", 1.0, 2.0) == []

def test_own_speech_cannot_wake():
    s = DeskState(); s.speaking_started(10.0)
    assert s.on_utterance("Yo Snoop here, three PRs merged", 10.2, 12.0) == []
    s.speaking_ended(13.0)
    assert s.on_utterance("Yo Snoop, CI?", 13.5, 14.0) == []      # starts inside the 1 s hold-off
    assert s.on_utterance("Yo Snoop, CI?", 14.5, 15.0) == [Ask("CI?")]

def test_stop_works_while_speaking_and_mutes_until_wake():
    s = DeskState(); s.speaking_started(10.0)
    assert s.on_utterance("peanut butter", 11.0, 11.5) == [Stop()]
    assert s.muted
    s.speaking_ended(11.6)
    assert s.on_utterance("Yo Snoop, CI?", 13.0, 14.0) == [Ask("CI?")]
    assert not s.muted

def test_empty_question_is_ignored():
    assert DeskState().on_utterance("Yo Snoop", 1.0, 1.5) == []

def test_strip_wake():
    assert strip_wake("Yo, Snoopy, any blockers?") == "any blockers?"
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/desk/state.py
import re
from dataclasses import dataclass
from yosnoop.wake import is_wake, is_stop

_WAKE_PREFIX = re.compile(r"^\W*(yo|you|yoh|yeah)\W+snoop(y|s)?\b\W*", re.IGNORECASE)


@dataclass(frozen=True)
class Ask:
    question: str

@dataclass(frozen=True)
class Stop:
    pass


def strip_wake(text: str) -> str:
    return _WAKE_PREFIX.sub("", text, count=1).strip()


class DeskState:
    def __init__(self, holdoff_s: float = 1.0):
        self.holdoff, self.muted = holdoff_s, False
        self._speaking_since, self._spoke_until = None, float("-inf")

    def speaking_started(self, t: float): self._speaking_since = t
    def speaking_ended(self, t: float): self._speaking_since, self._spoke_until = None, t

    def _blocked(self, start: float) -> bool:
        return self._speaking_since is not None or start < self._spoke_until + self.holdoff

    def on_utterance(self, text: str, start: float, end: float) -> list:
        if is_stop(text):
            self.muted = True
            return [Stop()]
        if self._blocked(start) or not is_wake(text):
            return []
        self.muted = False
        q = strip_wake(text)
        return [Ask(q)] if q else []
```

- [ ] **Step 3: Green** — 6 PASS. **Step 4: Commit** — `git add yosnoop/desk/state.py tests/test_desk_state.py && git commit -m "desk: state machine (wake, mute, self-voice hold-off)"`

---

### Task 4: Brain client, answer shaping, question log

**Files:** Create `yosnoop/brain_client.py`, `yosnoop/speech.py`, `yosnoop/qlog.py`, `tests/test_brain_client.py`, `tests/test_speech.py`, `tests/test_qlog.py`

**Interfaces:**
- `BrainClient(argv, first_line)`: `async start()`, `async ask(question, asker, room) -> BrainReply(ok, text, clone_age_s, reason)` (restarts once on exit → `reason="offline"`), `async stop()`; `production_argv()` = `["sudo", "-n", "-u", "snoop", str(bin_dir()/"brain")]`; `keychain_key()` via `security find-generic-password -s snoop-anthropic -a $USER -w` (stdout captured, never logged).
- `sentences(text)`; `shape(answer, clone_age_s) -> Shaped(spoken: list[str], full: str)` — `spoken = ["Snoop here.", ≤3 sentences]` + `"My notes are N minutes old."` when age > 1800 s; "peanut butter" replaced by "P B" everywhere.
- `qlog.write(entry, logdir, today=None)` with exactly `("ts","asker","room","question","outcome","latency_s")`; `qlog.prune(logdir, days=7, today=None)`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_brain_client.py
import asyncio, sys, textwrap
from yosnoop.brain_client import BrainClient

FAKE = textwrap.dedent('''
import json, sys
cred = None
for line in sys.stdin:
    m = json.loads(line)
    if m["type"] in ("key", "dev"): cred = m["type"]; continue
    if m["type"] == "ask":
        if m["question"] == "die": sys.exit(1)
        print(json.dumps({"type": "answer", "id": m["id"], "text": f"{cred}:{m['question']}", "clone_age_s": 1.0}), flush=True)
''')

def client(tmp_path):
    f = tmp_path / "fake_brain.py"; f.write_text(FAKE)
    return BrainClient([sys.executable, str(f)], {"type": "dev"})

def test_ask_round_trip(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r = await c.ask("hello", "Brett Evans", "team"); await c.stop(); return r
    r = asyncio.run(go())
    assert r.ok and r.text == "dev:hello"

def test_dead_brain_restarts_once_then_reports_offline(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r1 = await c.ask("die", "x", "team"); r2 = await c.ask("hello", "x", "team")
        await c.stop(); return r1, r2
    r1, r2 = asyncio.run(go())
    assert not r1.ok and r1.reason == "offline" and r2.ok
```

```python
# tests/test_speech.py
from yosnoop.speech import sentences, shape

LONG = "One. Two is here. Three? Four! Five."

def test_sentences():
    assert sentences(LONG) == ["One.", "Two is here.", "Three?", "Four!", "Five."]

def test_long_answer_speaks_three_and_keeps_full_text():
    s = shape(LONG, 60)
    assert s.spoken == ["Snoop here.", "One.", "Two is here.", "Three?"] and s.full == LONG

def test_stale_notes_are_disclosed():
    assert shape("CI is green.", 3600).spoken[-1] == "My notes are 60 minutes old."

def test_stop_phrase_is_scrubbed():
    s = shape("Ask Jeremy about peanut butter.", 60)
    assert "peanut butter" not in " ".join(s.spoken).lower() and "peanut butter" not in s.full.lower()
```

```python
# tests/test_qlog.py
import datetime, json, pytest
from yosnoop import qlog

E = {"ts": 1.0, "asker": "Brett Evans", "room": "desk", "question": "CI?", "outcome": "spoken", "latency_s": 2.1}

def test_write_has_exact_fields(tmp_path):
    qlog.write(E, tmp_path, today=datetime.date(2026, 10, 9))
    assert set(json.loads((tmp_path / "questions-2026-10-09.ndjson").read_text())) == set(qlog.FIELDS)

def test_write_rejects_extra_fields(tmp_path):
    with pytest.raises(ValueError):
        qlog.write({**E, "transcript": "room talk"}, tmp_path)

def test_prune_keeps_seven_days(tmp_path):
    for d in ("2026-09-30", "2026-10-02", "2026-10-09"):
        (tmp_path / f"questions-{d}.ndjson").write_text("{}")
    qlog.prune(tmp_path, days=7, today=datetime.date(2026, 10, 9))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["questions-2026-10-02.ndjson", "questions-2026-10-09.ndjson"]
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/brain_client.py
import asyncio, itertools, json, os, subprocess
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


def keychain_key() -> str:
    return subprocess.run(["security", "find-generic-password", "-s", "snoop-anthropic", "-a", os.environ["USER"], "-w"],
                          capture_output=True, text=True, check=True).stdout.strip()


class BrainClient:
    def __init__(self, argv, first_line: dict):
        self.argv, self.first, self.proc, self.ids = argv, first_line, None, itertools.count(1)

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(*self.argv, stdin=asyncio.subprocess.PIPE,
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        await self._send(self.first)

    async def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode()); await self.proc.stdin.drain()

    async def ask(self, question, asker, room, _retry=True) -> BrainReply:
        rid = str(next(self.ids))
        try:
            await self._send({"type": "ask", "id": rid, "question": question, "asker": asker, "room": room})
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=100)
            if not line:
                raise ConnectionError("brain exited")
            m = json.loads(line)
            if m["type"] == "answer":
                return BrainReply(True, m["text"], m.get("clone_age_s", float("inf")), None)
            return BrainReply(False, "", float("inf"), m.get("reason"))
        except (ConnectionError, BrokenPipeError, asyncio.TimeoutError):
            if _retry:
                await self.start()
            return BrainReply(False, "", float("inf"), "offline")

    async def stop(self):
        if self.proc and self.proc.returncode is None:
            self.proc.stdin.close()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError:
                self.proc.kill()
```

```python
# yosnoop/speech.py
import re
from dataclasses import dataclass

_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PB = re.compile(r"peanut\W+butter", re.IGNORECASE)


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    full: str


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text.strip()) if s.strip()]


def shape(answer: str, clone_age_s: float) -> Shaped:
    clean = _PB.sub("P B", answer)
    spoken = ["Snoop here."] + sentences(clean)[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    return Shaped(spoken, clean)
```

```python
# yosnoop/qlog.py
import datetime, json
from pathlib import Path

FIELDS = ("ts", "asker", "room", "question", "outcome", "latency_s")


def write(entry: dict, logdir: Path, today: datetime.date | None = None) -> None:
    if set(entry) != set(FIELDS):
        raise ValueError(f"question log entries carry exactly {FIELDS}")
    logdir.mkdir(parents=True, exist_ok=True)
    with open(logdir / f"questions-{(today or datetime.date.today()).isoformat()}.ndjson", "a") as f:
        f.write(json.dumps(entry) + "\n")


def prune(logdir: Path, days: int = 7, today: datetime.date | None = None) -> None:
    cutoff = (today or datetime.date.today()) - datetime.timedelta(days=days)
    for p in logdir.glob("questions-*.ndjson"):
        if datetime.date.fromisoformat(p.stem.removeprefix("questions-")) < cutoff:
            p.unlink()
```

- [ ] **Step 3: Green** — 9 PASS. **Step 4: Commit** — `git add yosnoop/brain_client.py yosnoop/speech.py yosnoop/qlog.py tests && git commit -m "brain client, answer shaping (Snoop here, 3 sentences, PB scrub), question log"`

---

### Task 5: Speaker — macOS `say` with immediate stop

**Files:** Create `yosnoop/desk/speak.py`, `tests/test_speak.py`

**Interfaces:** `Speaker(voice: str | None = None, runner=asyncio.create_subprocess_exec)`; `async speak(sentences, on_start, on_end)` speaks each sentence with `say`, stopping early if `stop()` is called; `async stop()` terminates the current `say` process.

- [ ] **Step 1: Failing tests** (fake runner records commands; a stop mid-list prevents later sentences)

```python
# tests/test_speak.py
import asyncio
from yosnoop.desk.speak import Speaker

class FakeProc:
    def __init__(self, log, text): self.log, self.text, self.returncode = log, text, None
    async def wait(self): await asyncio.sleep(0.05); self.returncode = 0
    def terminate(self): self.log.append(("terminate", self.text)); self.returncode = -15

def test_speaks_each_sentence_in_order():
    log = []
    async def runner(*cmd): log.append(cmd[-1]); return FakeProc(log, cmd[-1])
    events = []
    asyncio.run(Speaker(runner=runner).speak(["Snoop here.", "CI is green."], lambda: events.append("start"), lambda: events.append("end")))
    assert log == ["Snoop here.", "CI is green."] and events == ["start", "end"]

def test_stop_prevents_remaining_sentences():
    log = []
    async def runner(*cmd): log.append(cmd[-1]); return FakeProc(log, cmd[-1])
    async def go():
        s = Speaker(runner=runner)
        t = asyncio.create_task(s.speak(["One.", "Two.", "Three."], lambda: None, lambda: None))
        await asyncio.sleep(0.07); await s.stop(); await t
    asyncio.run(go())
    assert "Three." not in log
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/desk/speak.py
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
                cmd = ["say", *(["-v", self.voice] if self.voice else []), s]
                self.proc = await self.runner(*cmd)
                await self.proc.wait()
        finally:
            self.proc = None
            on_end()

    async def stop(self):
        self._stopped = True
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
```

- [ ] **Step 3: Green** — 2 PASS.
- [ ] **Step 4: Live stop latency** — a 10-sentence answer, then `await speaker.stop()` from another task after 2 s; time from `stop()` to the `say` process exit (expected ≤ 0.2 s) and, by ear, to silence. Record.
- [ ] **Step 5: Commit** — `git add yosnoop/desk/speak.py tests/test_speak.py && git commit -m "desk: say-based speaker with immediate stop"`

---

### Task 6: `./snoop desk` — wire it together

**Files:** Create `yosnoop/desk/run.py`, `tests/test_desk_wiring.py`

**Interfaces:**
- `DeskCtx(state, brain, speaker, stt, host_name, log, print_fn)`; `async handle_utterance(ctx, text, start, end)`; `run_desk(argv) -> int`.
- `run_desk`: load host (roster), print the earshot warning, `prepare()` (Plan 1), `qlog.prune`, start the brain (`production_argv()` + `{"type": "key", "value": keychain_key()}`; or `--dev` → `[sys.executable, "-m", "yosnoop.brain_main"]` + `{"type": "dev"}` with a warning), open a 16 kHz mono `sounddevice.InputStream`, run frames through `Endpointer`, transcribe utterances in a worker thread, call `handle_utterance`, refresh knowledge every 5 min, Ctrl-C stops cleanly.

- [ ] **Step 1: Failing wiring tests (fakes)**

```python
# tests/test_desk_wiring.py
import asyncio
from yosnoop.brain_client import BrainReply
from yosnoop.desk.run import DeskCtx, handle_utterance
from yosnoop.desk.state import DeskState

class Brain:
    def __init__(self, reply): self.reply, self.asked = reply, []
    async def ask(self, q, asker, room): self.asked.append((q, asker, room)); return self.reply

class Spk:
    def __init__(self): self.said, self.stopped = [], 0
    async def speak(self, ss, on_start, on_end): on_start(); self.said += ss; on_end()
    async def stop(self): self.stopped += 1

def ctx(reply):
    printed, logs = [], []
    c = DeskCtx(state=DeskState(), brain=Brain(reply), speaker=Spk(), host_name="Brett Evans",
                log=logs.append, print_fn=printed.append)
    return c, printed, logs

def test_question_is_answered_spoken_and_printed():
    c, printed, logs = ctx(BrainReply(True, "One. Two. Three. Four.", 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    assert c.brain.asked == [("CI?", "Brett Evans", "desk")]
    assert c.speaker.said == ["Snoop here.", "One.", "Two.", "Three."]
    assert printed[-1].endswith("One. Two. Three. Four.")
    assert logs[0]["outcome"] == "spoken" and logs[0]["question"] == "CI?"

def test_secret_answer_is_blocked():
    c, printed, _ = ctx(BrainReply(True, "key " + "ghp_" + "Q" * 36, 60, None))
    asyncio.run(handle_utterance(c, "Yo Snoop, key?", 1.0, 2.0))
    assert c.speaker.said == ["Snoop here, can't share that one."] and "ghp_" not in " ".join(printed)

def test_offline_brain():
    c, _, logs = ctx(BrainReply(False, "", 0, "offline"))
    asyncio.run(handle_utterance(c, "Yo Snoop, CI?", 1.0, 2.0))
    assert c.speaker.said == ["Snoop here, my brain's offline."] and logs[0]["outcome"] == "offline"

def test_peanut_butter_stops_speaker():
    c, _, logs = ctx(BrainReply(True, "x.", 60, None))
    asyncio.run(handle_utterance(c, "peanut butter", 1.0, 1.5))
    assert c.speaker.stopped == 1 and logs == []

def test_room_talk_is_not_logged():
    c, _, logs = ctx(BrainReply(True, "x.", 60, None))
    asyncio.run(handle_utterance(c, "we should snoop around the logs", 1.0, 2.0))
    assert logs == [] and c.brain.asked == []
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/desk/run.py
import asyncio, time
from dataclasses import dataclass
from typing import Callable
from yosnoop.desk.state import Ask, Stop
from yosnoop.gate import gate
from yosnoop.speech import shape

EARSHOT = "Desk Snoop answers out loud. Use it only when everyone who can hear it is on the Saasless team."


@dataclass
class DeskCtx:
    state: object
    brain: object
    speaker: object
    host_name: str
    log: Callable[[dict], None]
    print_fn: Callable[[str], None] = print


async def handle_utterance(ctx: DeskCtx, text: str, start: float, end: float) -> None:
    for a in ctx.state.on_utterance(text, start, end):
        if isinstance(a, Stop):
            await ctx.speaker.stop()
        elif isinstance(a, Ask):
            await _answer(ctx, a.question)


async def _answer(ctx: DeskCtx, question: str) -> None:
    t0 = time.monotonic()
    entry = {"ts": time.time(), "asker": ctx.host_name, "room": "desk", "question": question}
    reply = await ctx.brain.ask(question, ctx.host_name, "desk")
    on_start = lambda: ctx.state.speaking_started(time.monotonic())
    on_end = lambda: ctx.state.speaking_ended(time.monotonic())
    if not reply.ok:
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
```

Then `run_desk(argv)` in the same file, wiring: `roster = load(ROSTER)`, `host = hostcfg.load_host(roster)`, `print(EARSHOT)`, `prepare(host, dev)`, `qlog.prune(paths.secrets_dir().parent / "logs")`, `BrainClient(...)` as in the Interfaces block, `Transcriber()`, `Speaker()`, `Endpointer()`, a `sounddevice.InputStream(samplerate=16000, channels=1, dtype="float32", blocksize=1600)` callback that puts `(frame.copy()[:, 0], time.monotonic())` on an `asyncio.Queue` via `loop.call_soon_threadsafe`, a consumer task that feeds the endpointer and, per utterance, runs `await asyncio.to_thread(stt.transcribe, u.audio)` then `handle_utterance`; a refresher task every 300 s; `KeyboardInterrupt` → `brain.stop()`.

- [ ] **Step 3: Green** — `uv run pytest -q -m "not slow"` → all pass.
- [ ] **Step 4: Live desk smoke (Brett, alone)** — `./snoop desk --dev`. Allow the microphone prompt. Say "Yo Snoop, how many open pull requests are there?" Expected: the earshot warning at start; "Snoop here." then ≤ 3 sentences spoken; the full answer printed; one line in today's question log. Then a long question and "peanut butter" mid-answer: speech stops within ~1 s. Then talk normally for 30 s: nothing is logged.
- [ ] **Step 5: Wake accuracy at the desk** — read `spikes/p2_script.txt` (20 wake lines, 10 decoys) at the desk with `./snoop desk --dev` running in a log-only mode (`--dry` prints detected actions without asking the brain; add it with a test first). Pass: ≥ 18/20 wakes, 0/10 decoys, "peanut butter" detected.
- [ ] **Step 6: Commit and push** — `git add yosnoop tests && git commit -m "./snoop desk: mic → Whisper → brain → say" && git push`
