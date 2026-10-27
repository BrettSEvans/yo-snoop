# Phase 1a — Desk Rehearsal

Results record what was observed. Skipped steps say "skipped" and why.

## Brett install

`./snoop doctor`, 2026-10-18 18:00 PDT, as `snoop` with the Snoop key (sk-ant-, 108 chars, Keychain `snoop-anthropic`):

```
PASS  C0 snoop user, not admin, not staff; host home 700
PASS  C0b shared tree: real dirs, host-owned, not group/other-writable
PASS  C2 OS wall (host files unreadable as snoop, canary readable)
PASS  C9 Serena live tool list within keep list
PASS  C1 positive: reads its own knowledge
PASS  C3 app scope: read outside the knowledge dir denied
PASS  C4 tools: allowlist only, Serena read-only
PASS  C3b Serena read outside the knowledge dir refused
PASS  C5 key stripped from MCP children (unwrapped negative control = present)
PASS  C6 write attempt fails
PASS  C6b write to /tmp fails
PASS  C7 registry write refused; real registry unchanged
PASS  C8 key disclosure: no key-shaped text
```

Deviation from the runbook: the key was first typed at the zsh prompt instead of inside `security -i`; `security -i` takes Ctrl+D (not `quit`) to exit on this macOS. Runbook updated.

## Desk rehearsal (Brett)

| # | Line | Expected | Result (observed) | When (PDT) | By |
|---|---|---|---|---|---|
| D1 | "Yo Snoop, how many v1 to v2 gaps are there, and how many are missing?" | correct per the gap map; graded by Brett | | | |
| D2 | "Yo Snoop, how does an accessibility review run in v2?" | correct per `feat/AC-Version-2`; graded | | | |
| D3 | "Yo Snoop, where does multi-model support stand?" | correct per branches/PRs; graded | | | |
| D4 | "Yo Snoop, what does a v2 run cost compared with Beast Mode?" | correct per cost data; graded | | | |
| D5 | Every answer | starts "Snoop here."; ≤ 3 sentences spoken; full text printed | | | |
| D6 | Snoop's own speech | never wakes it (watch the log for a second question) | | | |
| D7 | "peanut butter" mid-answer | silence within ~1 s; next "Yo Snoop" works | | | |
| D8 | 30 s of normal conversation, no wake phrase | nothing logged, nothing asked | | | |
| D9 | Refresher paused 31 min | "My notes are 31 minutes old." | | | |
| D10 | Brain stopped (kill the `snoop` brain process) | "Snoop here, my brain's offline."; next question works after restart | | | |
| D11 | Question log | one line per question, exact fields, no other text | | | |
| D12 | Cost | Console `Snoop` workspace spend for the hour, and whether it drew on plan credits | | | |

## Pre-rehearsal checks run by Claude (2026-10-17, no microphone)

| Check | Result |
|---|---|
| Headless end-to-end (say-generated "Yo Snoop, how many open pull requests are there?" → endpointer → Whisper → `--dev` brain → gate → shaping) | Heard exactly; answered "There are 8 open pull requests…" (correct) in 7.7 s; one log line, outcome spoken |
| `say` stop latency (stop() → process exit) | 0.003 s |
| Whisper on say-generated wake / stop / decoy | wake detected, stop detected, decoy ignored |

## Wake accuracy — `spikes/p2_script.txt` (Brett, 2026-10-26, `./snoop desk --dry --debug`)

19 wake lines, 10 decoys, 1 stop line. Pass: ≥ 18/19 wakes, 0/10 decoys, stop detected.

| Read | Code | Wakes | Decoys woke | Stop | Notes |
|---|---|---|---|---|---|
| 1 | `f3ab3ea` (main) | 9/19 FAIL | 0/10 | yes | Mic speech 0.016–0.035 vs threshold 0.015 clipped starts; "Yes Snoop", "You go/gonna Snoop"; pause after "Yo Snoop" split the question off |
| 2 | `c702540` | 12/19 FAIL | 0/10 | yes | Louder mic (0.1–0.2). New mishearings: "You have Snoop", "No Snoop", "You don't snoop", "You have snooped"; line 28 lost "Yo Snoop" entirely |
| replay of 1 and 2 through `2fef73a` patterns | — | 17/19 and 18/19 | 0/10 | yes | Lexical stopgap. Detector plan parked after its license gate failed |
| 3: fresh lines, `spikes/p3_script.txt` | `87d4019` | 14/19 FAIL | 0/10 | yes | Misses: "You'll Snoop", "Your Snoop", "Good Snoop", bare "Snoop" then a pause, "Snoop emerged" ("who merged"). Whisper often drops "Yo" ("Snoop, …" still wakes). Lexical patterns don't generalize to unseen lines |
| 4: `spikes/p3_script.txt`, side by side (2026-10-27) | `1152b7d` | Whisper 17/19 FAIL; **Vosk 19/19** | Whisper 0/10; **Vosk 1/10 FAIL** ("he was snooping around the kitchen" → yo(1.00) snoop(1.00)) | yes | Whisper misses: "Your Snoop", "You have snipped". One off-script utterance ("You know Snoop, did you?") not scored; Vosk woke on it |
| Jeremy, `spikes/p3_script.txt` | | /19 | /10 | | at install |
| Lindsay, `spikes/p3_script.txt` | | /19 | /10 | | at install |
