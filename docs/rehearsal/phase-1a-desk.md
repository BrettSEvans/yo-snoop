# Phase 1a — Desk Rehearsal

Results record what was observed. Skipped steps say "skipped" and why.

## Brett install

(paste `./snoop doctor` output here)

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
