# Snoop Plan 3 — Desk Install Runbook and Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any roster member can install Desk Snoop on their own Mac from a written runbook, and Phase 1a passes a recorded desk rehearsal — Brett first, then Jeremy and Lindsay.

**Architecture:** `docs/RUNBOOK.md` (desk sections only; Plan 5 adds Meet sections later) and `docs/rehearsal/phase-1a-desk.md` (checklist with observed results). `./snoop doctor` gates every install.

**Tech Stack:** `./snoop` CLI (Plans 1–2), the Anthropic Console, macOS.

**Spec:** D13, D25 (rewritten), D31, D33–D40. Plans 1 and 2 must be complete.

## Global Constraints

- Each host uses their own Mac and their own Snoop API key from the **Console organization linked to their Max or Team plan** (D25), in one `Snoop` workspace with a spend limit.
- Keys go in through `security -i`; never on a command line, in chat, a doc, or a ticket.
- Results record what was observed. Skipped steps say "skipped" and why.
- Desk Snoop speaks aloud: run it only when everyone in earshot is on the team.

## Review Focus

1. **A second host's setup silently skips the lockdown** — expected: `./snoop doctor` fails and the install stops. Task 4, Step 3.
2. **Credits run out mid-rehearsal** — expected: "Snoop here, my brain's offline" style failure, not a silent hang; record what the brain returns. Task 3, row D10.
3. **Snoop wakes itself** — expected: never. Task 3, row D6.
4. **The runbook drifts from the CLI** — every command is executed in Task 2 or Task 4. Task 1, Step 2.
5. **Stale notes presented as current** — expected: the age disclosure after 31 minutes without a refresh. Task 3, row D9.

---

### Task 1: Write the desk runbook

**Files:** Create `docs/RUNBOOK.md`

- [ ] **Step 1: Write it** — sections, each with exact commands:
  1. **What you need:** a Mac you're admin on; `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`); Node; `gh` signed in with read access to `brett-saasless/Agent-C` and `brett-saasless/yo-snoop`; your entry in `config/team.json`; about 2 GB free disk (Whisper model + runtime).
  2. **Get the code:** `git clone https://github.com/brett-saasless/yo-snoop.git && cd yo-snoop`.
  3. **One-time setup:** `./snoop setup` (your email, shows the script, one admin password). Then `./snoop doctor` — every line PASS, or stop and send the output to Brett.
  4. **Your Snoop API key (uses your plan's monthly API credits):** link your Max or Team plan to the Saasless Console organization (claude.ai → Settings → Billing → API credits — Team owners do this once for the team); in the Console, `Snoop` workspace → create a key named for you; store it: `security -i`, then `add-generic-password -U -s snoop-anthropic -a <your mac username> -w <paste>`, then `quit`.
  5. **Microphone:** the first `./snoop desk` asks macOS for microphone access for your terminal app; allow it (System Settings → Privacy & Security → Microphone if you missed it).
  6. **Use it:** `./snoop desk`; say "Yo Snoop, …"; say "peanut butter" to stop it talking; Ctrl-C to quit. Only when everyone in earshot is on the team.
  7. **Update:** `git pull` (the next `./snoop desk` re-syncs the brain).
  8. **If something's wrong:** a short version of spec §6 for the desk, plus `./snoop doctor`.
- [ ] **Step 2: Verify every command** — each command is checked off when Brett runs it in Task 2 and a second host runs it in Task 4; anything that needed changing is fixed in the runbook the same day.
- [ ] **Step 3: Commit** — `git add docs/RUNBOOK.md && git commit -m "docs: desk runbook"`

---

### Task 2: Brett's install

- [ ] **Step 1:** Follow `docs/RUNBOOK.md` sections 1–6 exactly. Record deviations in the runbook.
- [ ] **Step 2:** `./snoop doctor` → all PASS (controls C0–C9). Paste the output under "Brett install" in `docs/rehearsal/phase-1a-desk.md`.
- [ ] **Step 3: Commit** — `git add docs && git commit -m "rehearsal: Brett desk install"`

---

### Task 3: Desk rehearsal (Brett)

**Files:** Create `docs/rehearsal/phase-1a-desk.md`

- [ ] **Step 1: Write the checklist with an empty Result column**

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

- [ ] **Step 2: Run it** — fill every row with what happened. Any FAIL on D5–D8 or D11 blocks rollout: fix in Plans 1–2 style (failing test first), rerun the row.
- [ ] **Step 3: Commit** — `git add docs/rehearsal/phase-1a-desk.md && git commit -m "rehearsal: Phase 1a desk results (Brett)"`

---

### Task 4: Jeremy's and Lindsay's installs

- [ ] **Step 1:** Each follows the runbook alone on their own Mac; Brett watches and does not type. Every point where they needed help becomes a runbook fix.
- [ ] **Step 2:** `./snoop whoami` → "Snoop (<their name>)".
- [ ] **Step 3: Negative control on their Mac** — after doctor passes: `chmod 750 $HOME` → doctor must FAIL C0 and C2; `chmod 700 $HOME` → PASS. Record.
- [ ] **Step 4:** Rows D1, D5, D6, D7 with them at their desk. Record under their name.
- [ ] **Step 5: Phase 1a done** — merge the branch to `main` with a PR in `brett-saasless/yo-snoop`; tag `v0.1.0-desk`.

```bash
git add docs
git commit -m "rehearsal: Phase 1a desk complete"
git push
```
