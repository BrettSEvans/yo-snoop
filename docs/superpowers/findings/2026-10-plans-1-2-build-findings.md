# Plans 1–2 Build Findings (2026-10-16 → 10-17)

What building the brain (Plan 1) and Desk Snoop (Plan 2) found that the plans did not say. Each item is something observed, not assumed. Code is on `main` (PR #1, merge `b2ebca6`).

## Security-relevant

| # | Finding | Evidence | What changed |
|---|---|---|---|
| 1 | Without a `tools=` allowlist the CLI exposes ~17 harness tools to the brain (RemoteTrigger, CronCreate/Delete, ScheduleWakeup, SendMessage, PushNotification, ShareOnboardingGuide, Workflow, EnterWorktree, Skill, …). The plan's `disallowed_tools` denylist missed them. | Init tool list of a live SDK session | `build_options` sets `tools=["Read","Grep","Glob"]`; doctor C4 asserts it |
| 2 | Serena 2.0.0's `agent` context ignores `read_only` and `fixed_tools`: it exposes editing tools and `execute_shell_command`. The `ide` context exposes exactly the 13-tool keep list. | Live `list_tools` per context | `--context ide` pinned; allowlist via `fixed_tools`; startup `assert_tools` |
| 3 | Working-directory read scoping holds: Read and Grep outside the knowledge dir are denied and reported in `ResultMessage.permission_denials`; a `../` Glob finds nothing. | Canary probe, also re-run by `doctor --dev` (C3) | Denials counted from `permission_denials` |
| 4 | Node and npm live under `~/.nvm`, inside the host's 700 home, so `snoop` can't run them. | Path check | Runtime gets a copy of node + npm only (~135 MB) |
| 5 | Serena rewrites `.serena/project.yml` on load (and leaves it 0600); an unwritable file is fatal. | Live runs | `prepare` does one host-side run, then chmods 644 |
| 6 | At home mode 750, `snoop` still can't read the host's files (it isn't in `staff`), so C2 passes; the plan expected a FAIL. 711 does expose files. | Negative controls | Doctor negative control uses 711 |
| 7 | Final reviews found no critical/high in Plan 1; one HIGH in Plan 2 (see Desk #1). All findings fixed. | Two fresh Opus reviews | See commit messages |

## Knowledge

- The full-repo map was ~5M tokens and tripped the secret scan on Agent-C's test fixtures (fake tokens). The map is now orientation docs only: 104,159 tokens, scan clean. Code is reached through Serena and file reads.
- `pr-ci-status.json` took the 30 newest PRs (all merged) and missed 8 older open PRs, so Snoop answered "zero open". Open PRs are now fetched separately with ready-made counts; the model then answers 8 (correct). Without counts it miscounted (7).
- Registry: 81 entries, 32 with `slug: null` (plan said 76/80), one duplicate slug, one id with a space. Bundle: 77 copied, 0 host paths in `registry.json`; key-shaped text redacted in every copied file.
- Agent-C's GitHub home is `Saasless-llc/Agent-C` (the `brett-saasless` URL redirects).

## Desk

| # | Finding | Evidence | What changed |
|---|---|---|---|
| 1 | "Peanut butter" said while Snoop talks was never heard: the endpointer can't cut speech that overlaps Snoop's voice, and Whisper (small.en) hears the overlapped phrase as "Do not bother". | Review + mixed-audio test | A stop watcher transcribes the last 1.5 s every 0.25 s while speaking, on its own `tiny.en` biased to "peanut butter": 5/6 cases caught, mostly 0.2–0.6 s after the phrase, 0/15 false stops. Miss: one voice with Snoop at 60% loudness |
| 2 | Whisper hears "Snoop" as snooze / smooth / smoot. | `say` voices over the 30-line script: 14/19 and 7/19 wakes | `hotwords="Snoop"`: 19/19 both voices, 0/10 decoys |
| 3 | Answer latency end to end (`--dev`): 5.5–7.7 s. Whisper small.en: ~0.9 s per utterance. Model: 484 MB. `say` stop: 0.003 s. | Headless runs | — |

## Still to verify with a person at the desk

- Real-voice wake accuracy (≥ 18/20, 0/10 decoys) and "peanut butter" stop by ear (Plan 2 Task 6 Steps 4–5; rehearsal D6–D8).
- `./snoop doctor` brain-turn controls as `snoop` (needs the Snoop API key in the Keychain).

## Wake-word gate (2026-10-26, wake-word plan Task 1)

The standard openWakeWord training recipe (`notebooks/automatic_model_training.ipynb`) pulls these inputs:

| Input | Role | License |
|---|---|---|
| openWakeWord code, `melspectrogram.onnx`, `embedding_model.onnx` | library + frozen feature models | Apache-2.0 |
| `rhasspy/piper-sample-generator` + `en_US-libritts_r-medium.pt` | synthetic "Yo Snoop" clips | MIT (generator); voice trained on LibriTTS-R (CC BY 4.0) |
| `davidscripka/openwakeword_features` (ACAV100M ~2,000 h features + false-positive validation set) | main negative data | **CC BY-NC-SA 4.0** |
| `davidscripka/MIT_environmental_impulse_responses` | room reverb | **unknown** |
| `rudraml/fma` (small) | background music | openrail (underlying FMA tracks carry mixed CC licenses) |
| `agkphysics/AudioSet` | background noise | CC BY 4.0 (card); audio originates on YouTube |

**Gate: FAIL.** The main negative set is non-commercial and the reverb set is unlicensed, so a model trained with the standard recipe can't ship at Saasless. No training was run.

Install check: `openwakeword==0.6.0` installs and imports on Python 3.12 / numpy 2.5.4 / onnxruntime 1.31.1 (scratch venv, deleted).
