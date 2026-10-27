# Snoop Wake-Word Detector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace "find 'Yo Snoop' in Whisper's transcript" with a trained on-device wake-word detector, so Desk Snoop wakes reliably for any roster member's voice, not just the mishearings seen in Brett's two script reads.

**Architecture:** An openWakeWord model trained for "Yo Snoop" scores every 80 ms of mic audio on the host's Mac. An utterance counts as a wake when the detector fired during it (or within the 5 s armed window after a bare wake), whatever Whisper wrote; Whisper still transcribes the question. The lexical patterns from 2026-10-26 stay as a fallback behind a flag until the detector beats them. An optional per-speaker verifier (`./snoop enroll`) is a later, separately approved task.

**Tech Stack:** `openwakeword` (Apache-2.0 code; ONNX inference on macOS via `onnxruntime`), its automatic training notebook (Google Colab, synthetic speech only), Plan 2's `yosnoop.desk` package.

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` — D7 (wake phrase "Yo Snoop"), D33, D37 (self-voice hold-off, stop phrase), §5.4. Evidence: `docs/superpowers/findings/2026-10-plans-1-2-build-findings.md` and the two desk reads in `docs/rehearsal/phase-1a-desk.md` (9/19, then 12/19; lexical patch replays 17/19 and 18/19; one wake lost from the transcript entirely).

## Global Constraints

- No audio or transcript leaves the Mac. Training uses synthetic speech generated in Colab; no recording of any person is uploaded.
- The model we ship is one we trained. openWakeWord's bundled pre-trained models are CC BY-NC-SA 4.0 and are never shipped or used in Snoop.
- Snoop is internal to Saasless (never customer-facing); a non-commercial clause on any training input still blocks shipping it (Task 1 gate).
- Audio stays in memory (Plan 2 rule). Task 6 (enrollment) changes this rule and needs Brett's explicit OK before it starts.
- Self-voice hold-off (1.0 s) and "peanut butter" behavior are unchanged; a detector firing while Snoop is speaking or inside the hold-off is ignored.
- Pass bar (D37 / rehearsal): ≥ 18/19 wakes, 0/10 decoys on `spikes/p2_script.txt`; plus 0 false wakes in 10 minutes of normal conversation; per host.
- Dry runs and scratch go under `~/.cache/snoop/`; models live in the repo under `models/` (small files), with their license and training config beside them.

## Review Focus

1. **Snoop's own speech fires the detector** — expected: ignored (hold-off), never an Ask. Task 4, `test_detector_fire_while_speaking_is_ignored`.
2. **A long question after one-breath "Yo Snoop, …"** — the fire lands near the start of a long utterance; expected: that utterance is the wake, the question is the rest. Task 4, `test_fire_near_start_of_long_utterance_counts`.
3. **Detector fires twice for one "Yo Snoop"** — expected: one wake (1.5 s refractory). Task 2, `test_refractory_suppresses_double_fire`.
4. **Sample-rate/frame mismatch** — sounddevice gives 1600-sample frames, openWakeWord wants 1280; expected: no dropped or duplicated samples across frames. Task 2, `test_reframing_preserves_every_sample`.
5. **Model file missing or corrupt on a fresh clone** — expected: `./snoop desk` falls back to lexical wake with a printed warning and `./snoop doctor` reports it; never a crash. Task 5, `test_missing_model_falls_back_with_warning`.

---

### Task 1: Gate — licenses, install, and feasibility on this Mac

**Files:** Create `models/README.md`; modify `docs/superpowers/findings/2026-10-plans-1-2-build-findings.md` (new "Wake-word gate" section).

- [ ] **Step 1: License check.** Record, with links, the license of: openWakeWord code; the feature models `melspectrogram.onnx` and `embedding_model.onnx` (downloaded by `openwakeword.utils.download_models`); every dataset and TTS model the automatic training notebook (`notebooks/automatic_model_training.ipynb`, and the Colab it links) pulls in — positive-clip TTS voices (piper-sample-generator) and the negative/background feature sets. **Gate:** if any input is non-commercial or unknown, stop, ledger it, and bring Brett the options (train only on cleanly licensed inputs; or Picovoice Porcupine custom keyword, paid; or keep the lexical stopgap). Do not train.
- [ ] **Step 2: Install check.** `uv add --optional desk openwakeword` into a scratch copy first; record the resolved versions of `openwakeword`, `onnxruntime`, `numpy`, and whether `import openwakeword; openwakeword.utils.download_models([])` works on Python 3.12 / numpy 2.x. If the 2024 release breaks on numpy 2, pin a git commit of `dscripka/openWakeWord` that works (record the SHA) — never vendor its pre-trained models.
- [ ] **Step 3: Write `models/README.md`**: what each file is, its license, how it was trained (points to Task 2's config), and "bundled openWakeWord pre-trained models are not used".
- [ ] **Step 4: Commit** — `git add models/README.md docs pyproject.toml uv.lock && git commit -m "wake-word gate: licenses and install check"`

### Task 2: Train the "Yo Snoop" model

**Files:** Create `training/yo_snoop.yml` (the notebook's config: target phrases, negative phrases, sample counts, steps), `models/yo_snoop.onnx`, `tests/test_wake_model_slow.py`.

- [ ] **Step 1: Write the config.** Target phrases: "yo snoop", "yo, snoop", "yo snoopy". Adversarial negatives (verbatim from the desk reads and script decoys): "snoop", "snoop dogg", "we should snoop around", "don't snoop", "you should snoop", "let's not snoop", "snooping", "snoopy", "yo", "you know", "no problem", "you have". Sample count and training steps: the notebook's recommended production values (record them).
- [ ] **Step 2: Run the training** in the Colab notebook (Brett starts it under his Google account; Claude prepares the config and reads back the logs). Only synthetic speech is generated; nothing from the Mac is uploaded. Download `yo_snoop.onnx` into `models/`.
- [ ] **Step 3: Failing slow test (before the file exists)**

```python
# tests/test_wake_model_slow.py
import numpy as np, pytest
from tests.helpers import say_to_array

@pytest.mark.slow
@pytest.mark.parametrize("voice", ["Samantha", "Daniel", "Fred"])
def test_model_fires_on_yo_snoop_and_not_on_decoys(voice):
    from yosnoop.desk.wakeword import WakeDetector
    def fires(text):
        d = WakeDetector("models/yo_snoop.onnx")
        a = np.concatenate([np.zeros(8000, np.float32), say_to_array(text, voice=voice), np.zeros(16000, np.float32)])
        return any(d.feed(a[i:i + 1600], i / 16000) is not None for i in range(0, a.size, 1600))
    assert fires("Yo Snoop, how many open pull requests are there?")
    for decoy in ("We should snoop around the logs later", "Snoop Dogg had a new album out", "Don't snoop"):
        assert not fires(decoy)
```

(`say_to_array` gains an optional `voice` parameter in this task.)

- [ ] **Step 4: Run it after Task 3 lands** → PASS for all three voices. Record per-voice max scores for wakes and decoys in the findings.
- [ ] **Step 5: Commit** — `git add training models tests && git commit -m "wake-word: yo_snoop model trained on synthetic speech"`

### Task 3: `WakeDetector`

**Files:** Create `yosnoop/desk/wakeword.py`, `tests/test_wakeword.py`.

**Interfaces:**
- Produces: `WakeDetector(model_path: str, threshold: float = 0.5, refractory_s: float = 1.5, predict=None)`; `feed(frame: np.ndarray, t: float) -> float | None` (returns the fire time, in the same clock as `t`, or None); `last_score: float` (for `--debug`). `predict` injects a fake `(chunk_1280: np.ndarray) -> float` for tests; default wraps `openwakeword.model.Model(wakeword_models=[model_path], inference_framework="onnx").predict`.

- [ ] **Step 1: Failing tests** in `tests/test_wakeword.py`:
  - `test_reframing_preserves_every_sample` — feed 1600-sample frames numbered 0…N; a recording fake `predict` receives consecutive 1280-sample chunks whose concatenation equals the input prefix exactly.
  - `test_fires_once_when_score_crosses_threshold` — fake returns 0.1, 0.7, 0.8; exactly one non-None result, at the time of the chunk that first scored ≥ 0.5.
  - `test_refractory_suppresses_double_fire` — scores ≥ 0.5 on chunks 0.5 s apart fire once; again after 1.6 s fires twice.
  - `test_fire_time_is_chunk_end_time` — fire time equals `t` of the frame plus the offset of the chunk end within it (rate 16000).
- [ ] **Step 2: Run** `uv run pytest tests/test_wakeword.py -q` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** in `yosnoop/desk/wakeword.py`. A carry-over buffer reframes to 1280 samples; the default `predict` converts float32 [-1, 1] to int16 as openWakeWord expects and returns the model's score for `yo_snoop`.
- [ ] **Step 4: Run** → PASS; then `uv run pytest -q -m slow tests/test_wake_model_slow.py` → PASS (needs Task 2's model).
- [ ] **Step 5: Commit** — `git add yosnoop/desk/wakeword.py tests/test_wakeword.py && git commit -m "desk: WakeDetector (openWakeWord, reframing, refractory)"`

### Task 4: Wake from the detector in the state machine

**Files:** Modify `yosnoop/desk/state.py`; test `tests/test_desk_state.py`.

**Interfaces:**
- Consumes: Plan 2's `DeskState`, `Ask(question, stop_seq)`, `strip_wake`, `ARMED_S`.
- Produces: `DeskState.on_utterance(text, start, end, wake_heard: bool = False, lexical: bool = True) -> list`. `wake_heard=True` makes the utterance a wake whatever the text says; the question is `strip_wake(text)` (a leftover "Yo Snoop" in the transcript is removed); empty → arms the 5 s window as today. `lexical=False` disables the transcript patterns.

- [ ] **Step 1: Failing tests:**
  - `test_detector_wake_with_mangled_transcript` — `on_utterance("What's agency 1252 about?", 1, 3, wake_heard=True) == [Ask("What's agency 1252 about?")]` (Brett's read-2 line 28).
  - `test_detector_fire_while_speaking_is_ignored` — after `speaking_started(10)`, `on_utterance("anything", 10.5, 11, wake_heard=True) == []`.
  - `test_fire_near_start_of_long_utterance_counts` — `wake_heard=True` with a 12 s utterance asks with the stripped text.
  - `test_lexical_off_ignores_transcript_wakes` — `on_utterance("Yo Snoop, CI?", 1, 2, lexical=False) == []`.
  - Every existing state test still passes unchanged.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** — `git add yosnoop/desk/state.py tests/test_desk_state.py && git commit -m "desk: detector-driven wake in the state machine"`

### Task 5: Wire the detector into `./snoop desk`

**Files:** Modify `yosnoop/desk/run.py`, `yosnoop/doctor.py`, `docs/RUNBOOK.md`; test `tests/test_desk_wiring.py`.

**Interfaces:**
- Consumes: `WakeDetector` (Task 3), `DeskState.on_utterance(..., wake_heard, lexical)` (Task 4).
- Produces: `load_detector(path: Path) -> WakeDetector | None` (None + a printed warning when the file is missing or fails to load); `wake_in(fires: list[float], start: float, end: float, slack_s: float = 0.3) -> bool`; `handle_utterance(ctx, text, start, end, wake_heard=False)`; desk flags `--wake=detector|lexical|both` (default `both` until Task 7 passes, then `detector`).

- [ ] **Step 1: Failing tests:**
  - `test_wake_in_window` — fires `[5.0]`: `wake_in(.., 4.8, 9.0)` True; `wake_in(.., 5.4, 9.0)` False; `wake_in(.., 4.5, 4.75)` True (slack covers a fire just after the endpointer cut).
  - `test_missing_model_falls_back_with_warning` — `load_detector(Path("nope.onnx"))` returns None and prints "wake model missing; using transcript wake"; `run_desk` then uses `lexical=True`.
  - `test_doctor_reports_wake_model` — doctor gets a `W1 wake model present and loads` line; FAIL text names the path.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** Feed the detector every frame (before the endpointer); keep fire times for 30 s; pass `wake_heard=wake_in(...)` per utterance; `--debug` prints the peak score each second next to the mic level. The model loads once at start. **Step 4: Run** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** — `git add yosnoop docs tests && git commit -m "./snoop desk: detector wake with lexical fallback; doctor W1"`

### Task 6 (needs Brett's OK first): Per-speaker verifier — `./snoop enroll`

Spec change: enrollment writes a few seconds of the host's audio to `~/.config/snoop/enroll/` (700) long enough to train, then deletes it; only the verifier (`~/.config/snoop/wake-verifier.pkl`) is kept. Start only after Brett approves that change and Task 7 shows the base model alone misses the pass bar for some host.

**Files:** Create `yosnoop/desk/enroll.py`, `tests/test_enroll.py`; modify `yosnoop/cli.py`, `yosnoop/desk/wakeword.py` (`verifier_path`).

- [ ] **Step 1: Failing tests:** `test_enroll_deletes_audio_after_training` (fake recorder and fake `train_custom_verifier`; afterwards `enroll/` is empty and the `.pkl` exists, mode 600); `test_enroll_prompts` (3 × "Say: Yo Snoop", then "Talk normally for 10 seconds without saying Yo Snoop").
- [ ] **Step 2–4:** RED → implement with `openwakeword.train_custom_verifier(positive_reference_clips, negative_reference_clips, output_path, model_name="models/yo_snoop.onnx")` → GREEN.
- [ ] **Step 5: Commit** — `git commit -m "./snoop enroll: per-speaker wake verifier (audio deleted after training)"`

### Task 7: Measure, then switch the default

**Files:** Modify `docs/rehearsal/phase-1a-desk.md`, `yosnoop/desk/run.py` (default `--wake`).

- [ ] **Step 1: Brett, script read** with `./snoop desk --dry --debug --wake=detector`: ≥ 18/19 wakes, 0/10 decoys, stop detected. Record next to reads 1–2.
- [ ] **Step 2: Fresh lines** — five new "Yo Snoop" questions and five sentences using "snoop": 5/5 and 0/5.
- [ ] **Step 3: False-accept soak** — 10 minutes of normal conversation or a podcast at desk volume with `--dry --debug --wake=detector`: 0 wakes.
- [ ] **Step 4: Same for Jeremy and Lindsay** at their desks (Plan 3 Task 4); if one misses the bar, Task 6 becomes the next step for that host.
- [ ] **Step 5:** If Steps 1–3 pass, make `detector` the default and keep `lexical` as an explicit fallback flag. Commit — `git commit -m "desk: detector wake by default (rehearsal: <numbers>)"`
