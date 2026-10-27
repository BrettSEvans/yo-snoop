# Plan 0 findings

Spec: docs/superpowers/specs/2026-10-05-yo-snoop-design.md · Plan: docs/superpowers/plans/2026-10-05-plan-0-verification-spikes.md

| Probe | Spec ref | Verdict | Evidence below | Consequence for Plans 1–2 |
|---|---|---|---|---|
| P1 Meet participants principal + latency | §8.1, §4 step 4 | | | |
| P2 Caption reading in the extension + wake accuracy | §8.2, §4 step 3 | **Reading HOLDS. Wake from captions HOLDS with a pause after "Yo Snoop"** (5/5, 0/2 decoys, stop 1/1); run together it fails (1-2/12) | §P2 | Meeting wake is "Yo Snoop!" alone, then the question within a few seconds (desk's armed window); scored run with another reader still due |
| P3 Claude Code headless controls | §8.3, §5.3 | **PARTIAL** — Steps 1–5 HOLD; Step 6 (key helper) deferred to Plan 1 (D25) | §P3 | Plan 1 uses the SDK with `setting_sources=[]`, `strict_mcp_config`, `dontAsk`; `--max-turns` is SDK-only |
| P4 Voice + card via extension (BlackHole fallback) | §8.4, D28, D29, D42 | **HOLDS** (2026-10-27, extension path; stop latency by ear, not yet measured on a recording) | §P4 | The meeting seat speaks Onyx through the extension; no BlackHole needed |
| P5 Chat app, team group, one space | §8.5, §3.3 | | | |
| P6 Own-voice label | §8.6, D30 | **HOLDS** (2026-10-27): own speech is always captioned `You`; a peanut-butter caption stopped Snoop mid-speech 3/3 | §P6 | `own_label = "You"`: the seat ignores its own captions; stop works from captions while speaking |
| P7 Two-Snoop detection | §8.7, D32 | Logic written and tested (`spikes/p7_seats.py`, 5/5); live run needs a second roster member | §P6 | — |

Obsolete after the 2026-10-06 revision (D26): old P4 "Attendee SAML, OU-scoped" and old P6 "Attendee audio stop latency" — never run.

Verdicts: HOLDS / FAILS / PARTIAL. Every verdict cites pasted command output. No secrets.

## P3 — Claude Code headless controls (2026-10-05, Claude Code 2.1.283, claude-agent-sdk 0.2.163)

**Step 1, signature probe** (`bash spikes/p3_flags.sh`): PRESENT `--allowedTools`, `--disallowedTools`,
`--permission-mode` (choices `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan`), `--settings`,
`--mcp-config`, `--strict-mcp-config`, `--input-format`, `--output-format`, `--resume`, `--continue`,
`--append-system-prompt`, `--setting-sources`. **ABSENT: `--max-turns`** (CLI). The SDK's
`ClaudeAgentOptions` has `max_turns`, `max_budget_usd`, `setting_sources`, `strict_mcp_config`,
`permission_mode` (incl. `dontAsk`), `allowed_tools`, `disallowed_tools`, `sandbox`, `can_use_tool`, `hooks`;
`ClaudeSDKClient` exists. `--help` mentions `apiKeyHelper via --settings`.

**Steps 2–3, sandbox probe** (`uv run python -m spikes.p3_sandbox_probe`), isolated with
`--setting-sources project --strict-mcp-config --permission-mode dontAsk`, allow `Read, Grep, Glob, Bash(git log:*)`:

```
2026-10-05 17:05:35 PDT {
  "positive_read": true,
  "negative_write_blocked": true,
  "negative_network_blocked": true,
  "negative_shell_blocked": true
}
rc=0
```

**Step 4, negative control** (same probe with `Write` allowed and removed from deny):

```
2026-10-05 17:06:07 PDT {
  "positive_read": true,
  "negative_write_blocked": false,
  "negative_network_blocked": true,
  "negative_shell_blocked": true
}
rc=1
```

The probe detects a write when one is permitted, so the clean run in Step 3 is evidence.

**Step 5, one session, two questions** (`uv run python -m spikes.p3_session_probe`, SDK, `setting_sources=[]`):
q1 "ok" in 1.43 s, `cache_creation_input_tokens` 14,049; q2 "You asked me to remember 4182." in **0.97 s**,
`cache_read_input_tokens` **14,049**. Context carries across questions in one `ClaudeSDKClient` session and
the prefix is served from cache (1-hour ephemeral cache). Supports D22's one-session-per-meeting design.

**Step 6, API key helper:** not run — needs the owner's Snoop Console key in Keychain (see plan Task 3 Step 6).

**Consequences for Plan 1:** use the SDK (`ClaudeSDKClient`) for the brain, not the CLI, because only the SDK
has `max_turns`/`max_budget_usd`; always pass `setting_sources=[]`, `strict_mcp_config=True`,
`permission_mode="dontAsk"`, explicit `allowed_tools`. Repeat the Step 2–4 controls as the `snoop` user in Plan 1.

**P3 addendum (2026-10-05):** Claude Code 2.1.283 has `--bare` — minimal mode that skips settings/plugin
hooks, LSP, plugin sync, auto-memory, keychain reads and CLAUDE.md auto-discovery; in it, Anthropic auth is
**strictly `ANTHROPIC_API_KEY` or `apiKeyHelper` via `--settings` (OAuth and keychain are never read)**.
Consequences: Plan 1 should run the brain in bare mode (or the SDK equivalent) for isolation; and the
production brain cannot run on a personal claude.ai subscription login in that mode — it needs an API key.
Plan 0 testing on the owner's own login is unaffected.

**P3 addendum 2 — subscription vs API key (2026-10-05, owner question).** Anthropic's support article
"Use the Claude Agent SDK with your Claude plan": Agent SDK and `claude -p` use is available on Pro, Max,
Team and Enterprise for "your own projects"; credits "can't be shared or pooled across teammates";
and "Teams running shared production automation should use Claude Platform with an API key."
The announced separate monthly SDK credit is **paused** — SDK and `claude -p` usage currently draw from the
plan's normal usage limits (shared with the owner's own Claude Code and chat use).
Decision D25: Plans 0–2 development may use the owner's subscription; team-facing Snoop uses an API key.
Task 3 Step 6 (apiKeyHelper) is therefore deferred to Plan 1's production config, not needed for Plan 0's verdicts.
Source: https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan


## Corrections after the adversarial review (2026-10-09)

Report: `docs/product/critic-reports/2026-10-09-session-aec42f1e-orchestrator-contract.md`.

- **`--max-turns` exists.** It is hidden from `claude --help`, but `claude -p hi --max-turns 0` runs and the SDK passes it to the CLI. The earlier "ABSENT / SDK-only" line is wrong.
- **P3 proved less than recorded.** Only the write check was shown able to fail. The network and shell checks were never shown able to detect anything, `claude -p` errors were ignored, and the probe ran a different configuration (`--setting-sources project` + `--settings`, CLI 2.1.283) from production (`setting_sources=[]`, bundled CLI 2.1.286). P3's verdict is downgraded to **INCONCLUSIVE except the write check**; Plan 1 Task 9 re-runs every control through the SDK as `snoop`, asserting permission-denial events and no errors.
- **Subscription and credits:** see spec D25 (rewritten): Max and Team plans include monthly API credits from 2026-10-07.
- **Serena pin:** the #1938 fix is unreleased on PyPI (1.7.0 predates it); Plan 1 pins a git commit.

## Setup log

2026-10-27, done by Brett, guided by Claude (Plan 0 Task 2):

- Google Cloud project `yo-snoop` under saasless.ai. Enabled: Google Meet REST API, Google Chat API, People API. Cloud Text-to-Speech is **not** enabled (D42: the voice is Onyx on the Mac). No billing or free trial.
- Google Auth Platform: app "Snoop", audience **Internal**.
- OAuth client "Snoop desktop" (Desktop app; the "AI-powered agent" box left unticked). Its JSON is at `spikes/.secrets/client_secret.json`: mode 600, git-ignored, project `yo-snoop`. Checked by shape only; never printed.
- Google Group `snoop-team@startup.ai`: Restricted, no outside members. Members brett@, jeremy@ and lindsay@, matching `config/team.json`.
- Chrome profile **Snoop**. Plan deviation: Chrome allows only one profile per signed-in account, and brett@ already has one. So the Snoop profile is **not signed in to Chrome** (no sync at all), and brett@ is signed in to the web only, for Meet.

## P2: reading Meet captions (2026-10-27, partial)

Done by Brett, alone, with the Snoop seat in the Snoop Chrome profile and a second seat as himself.

- **The caption region is readable from the extension.** It's `[role=region][aria-label="Captions"]`, with one `div.nMcdL` per speaker turn: the speaker name is in `span.NWpY1d` and the text is in `div.ygicle`. Class names are generated by Meet; the region is found by role and label. The sanitized fixture is `spikes/extension/test/fixture_captions.html`, and the real capture was deleted.
- **Live:** caption text reaches the listener word by word, within about 1 s of speech, as the line grows. "Peanut butter" was flagged STOP. "We should snoop around the logs" was not a wake.
- **Meet rewrites captions while you talk** ("Yes, Snoop" became "Yo Snoop" about 1 s later), and it keeps a speaker's turn in one block across sentences. So wake checks run on the latest sentence, once it settles.
- **Meet mishears "Snoop" too:** "Snipes", "Snips", "slip", and one line came through as "This new backyard?". Vosk can't help in a meeting, because Snoop only gets caption text. The scored wake run (Step 7, another person reading `spikes/p2_script.txt`) decides whether caption text is good enough.
- **The Snoop seat replaces the mic and camera:** its tab sends Snoop's voice and the name card ("Snoop (Brett Evans)"), so a person speaks from a second seat. Plan 0 Task 6 Step 1 assumed Brett speaks in the Snoop tab; that can't work.
- **Speaker labels:** both seats are brett@, and Meet credited speech from someone else in Brett's room to "Brett Evans". So the asker check has to treat a seat's label as "anyone near that mic".
- **Fixes along the way:**
  - The extension config must be readable by Chrome (0644).
  - A spike test used to delete the live config; fixed.
  - The service worker now pings every 20 s, so Chrome doesn't put it to sleep.
  - Content-script ports reconnect after a worker restart.

Still to do for P2:
- Step 7, the scored run with another reader, from the phone or another Mac to avoid echo.
- Check that a turn split across a pause reads whole: the reader now joins every text piece, but this hasn't been confirmed live.

### P2 phone retest (2026-10-27, 15:02-15:05 PDT)

Brett spoke from his phone (a separate device, so no echo) while the Snoop seat read captions on the Mac. There were three runs of the same five lines:

| Line | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| wake: is CI green | "Snoop is CI green." WAKE | "Your Snap is CI green." | "Yo Snippets, the CI green." |
| decoy: snoop around the logs | ignored | ignored | ignored |
| wake: how many PRs merged | "Yo, Steve, how many PR is merged?" | "You'll snip…", then "How many PR's merged?" | "Your snip?", then "How many PR's merged?" |
| wake: who opened the newest PR | "Does Snoop who opened the newspr?" | "Nip, who opened the newest PR." | "They pull up in the newest PR." |
| stop: peanut butter | STOP | "Una Para." | "Nut butter." |

Another wake line in run 1 matched mid-sentence ("Yes, Snoop on APRs…") and then Meet rewrote it as "Some aprs are open."

**Totals:** wakes 1-2/12 (bar ≥ 18/19), stops 1/3, false wakes 0/3. Meet transcribes the **question** well but not "Yo Snoop" or "peanut butter". **Verdict: wake and stop from caption text FAIL.**

Proposed next spike: the Snoop seat already receives the meeting audio. Pass it from the extension to the host's Mac, in memory and never saved, and run the desk's wake and stop checks on it: Vosk ("yo snoop", 19/19 on Brett at the desk) and the "peanut butter" watcher. Captions still supply the question's words. This amends D8 (speech in), and needs Brett's go.

### P2b: meeting-audio tap, parked; the pause fixes captions (2026-10-27, 15:20-15:37 PDT)

**Audio tap (parked).** The Snoop seat hooked Meet's incoming audio: RTCPeerConnection tracks plus Meet's own players, with a muted player per track, at 16 kHz and then at Chrome's 48 kHz. It found **3 meeting audio streams** with the engine running, but read **pure silence** (peak 0.000) while Brett talked and captions flowed. Chrome doesn't give an extension readable audio from Meet's streams this way. The next route would have been Chrome tab capture (`tabCapture` + an offscreen page, one click per meeting). It isn't needed (below). The code was removed; it stays in git history (b0de48f..d3acbac).

**The pause.** Said as "Yo Snoop!", a beat, then the question, Meet captions it cleanly:

| Run | Wakes | Decoys woke | Stop |
|---|---|---|---|
| 15:34 (pause, informal) | 2/2 | 0/1 | not said |
| 15:36 (pause, 5 lines) | 3/3 | 0/1 | 1/1 ("Peanut butter.") |
| earlier, run together (3 runs) | 1-2/12 | 0/3 | 1/3 |
| 15:36:36, one line rushed just before the paused run | 0/1 ("Go Snippets CI green!") | — | — |

The question arrives as its own clean caption ("Is CI green?", "Who opened the newest PR?"). So the meeting seat uses the desk's bare-wake rule: a caption sentence that is only a wake opens a ~5 s window, and the next sentence from the same speaker is the question. "Yo Snoop, …" all in one sentence still works when Meet hears it ("Yo Snoop what's happening now?").

**Still due:**
- The scored run with another reader (Jeremy or Lindsay), using the pause, to confirm on a second voice.
- "Peanut butter" over Snoop's own voice. That's P4/P6 territory, because the Snoop seat's own speech isn't in its captions.

## P4: Snoop's voice and card in the meeting (2026-10-27, 15:42-15:55 PDT)

Brett, solo. The Snoop seat was in the Snoop Chrome profile, and Brett's phone (as brett@) was the listener. Probe: `spikes/p4_media.py`, a 33 s Onyx paragraph (Kokoro, D42) sent in 1 s chunks over the bridge, played by `page_media.js` into the seat's injected mic.

| Step | Result |
|---|---|
| 2. Positive control | **Pass.** Onyx was heard clearly on the phone, and the "Snoop (Brett Evans)" card showed as the seat's video. The first try went unheard only because the phone's volume was down. |
| 3. Negative control (real mic not used) | **Pass.** The phone's own mic was muted. While Snoop was idle, Brett talked near the laptop for about 10 s, and Snoop's tile stayed still. It lit up when Snoop talked. |
| 4. Stop latency | **Pass by ear:** it "stops right away". It was not yet measured from a screen recording against the 1.0 s bar. |
| 5. Device re-open | **Pass via the camera:** off and on, the card came back and Onyx still played. Switching the mic wasn't possible, because only one input device was listed. |

**Verdict: HOLDS on the extension path.** The BlackHole fallback isn't needed. To carry into Plan 4:
- The seat must join **unmuted**, or tell the host that it's muted.
- Its own speech is not in its captions. Stop-while-speaking and own-voice exclusion are P6.

## P6: own-voice label and stop while speaking (2026-10-27, 15:55-15:58 PDT)

Brett, solo. The Snoop seat was in the Snoop profile with CC on, and his phone (brett@, mic on) was in the same meeting. Probe: `spikes/p6_loop.py`, with Onyx talking through the seat while captions were read.

- **Own-voice label:** all **165** caption lines of Snoop's own speech, across 4 talking runs, came through labeled **`You`**. Brett's phone came through as `Brett Evans`. No other speaker ever got `You`. Snoop's own speech is captioned, including its "Snoop here" lines, so the seat **must ignore `You`** to avoid waking or standing down on itself. The P7 rule `is_own_seat(speaker, "You")` covers this.
- **Stop while speaking:** Brett said "peanut butter" on the phone while Snoop talked. Meet captioned it as `Brett Evans | Peanut butter.` even over Snoop's speech: captions are per participant, so overlap doesn't garble the way it did at the desk. Snoop went silent **0.13 s, 0.24 s and 0.02 s** after the caption arrived (**3/3**). The time from the words to the caption was not measured. Captions run about 1 s behind speech (P2), so the spoken-word-to-silence total is roughly 1 s.
- Meet's profanity filter shows up in captions (`m***********`); that's irrelevant to stops.

P7 (two Snoops): `stand_down` is written and unit-tested (5/5). The live step, where another roster member's seat says "Snoop here", needs Jeremy or Lindsay.
