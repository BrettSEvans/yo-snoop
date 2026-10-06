# Snoop Plan 3 — Install Runbook and Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any roster member can install Snoop on their own Mac from a written runbook, and Phase 1 passes the spec §9 rehearsal — Brett first, then Jeremy and Lindsay.

**Architecture:** A runbook (`docs/RUNBOOK.md`) plus a rehearsal checklist with a results table (`docs/rehearsal/phase-1.md`). The checklist is the acceptance record: every line has a result, a date (PDT) and who ran it. `./snoop doctor` (Plan 1) gates every install.

**Tech Stack:** The `./snoop` CLI (Plans 1–2), Chrome, Google Meet, Google Chat, the Anthropic Console.

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` §9 and D13, D26–D36. Plans 1 and 2 must be complete.

## Global Constraints

- Each host uses **their own** Google account, Mac, and Snoop API key (D13). Nobody installs on someone else's account.
- Keys go in through `security -i` (never on a command line); nobody pastes a key into chat, a doc, or a ticket.
- Rehearsal results are recorded with what was observed, not what was expected. A step that was skipped says "skipped" and why.
- Before first use, every roster member is told Snoop hears the whole all-team meeting and sits in the host's seat (spec §4, pre-loading note applies in Phase 2; the seat note applies now).

## Review Focus

1. **A second host's install silently skips the home lockdown** — expected: `./snoop doctor` FAILs and the install stops. Task 4, Step 3.
2. **Two Snoops answer at once** — expected: the lower-priority one stands down after the first answer. Task 5, Step 2.
3. **A guest hears an answer** — expected: never. Task 3, rehearsal lines R5–R8.
4. **The runbook drifts from the CLI** — expected: every command in the runbook is executed during Task 2 or Task 4. Task 1, Step 2.
5. **Stale notes presented as current** — expected: "My notes are N minutes old" after the refresher is stopped for 31 minutes. Task 3, line R11.

---

### Task 1: Write the runbook

**Files:**
- Create: `docs/RUNBOOK.md`

- [ ] **Step 1: Write it** — sections, in order, each with the exact commands:
  1. **What you need:** a Mac you have admin on; Chrome; `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`); Node; read access to `brett-saasless/Agent-C` and `brett-saasless/yo-snoop`; your entry in `config/team.json`; membership in `snoop-team@startup.ai`.
  2. **Get the code:** `git clone https://github.com/brett-saasless/yo-snoop.git && cd yo-snoop`.
  3. **One-time setup:** `./snoop setup` (asks your email, shows the script, one admin password). Then `./snoop doctor` — all PASS or stop.
  4. **Your Google pieces:** copy the shared `client_secret.json`, `tts-key.json`, `chat-key.json` your admin gives you into `~/.config/snoop/secrets/` (each host gets their own service-account keys); write `~/.config/snoop/chat.json` `{"space": "spaces/…"}`; run `./snoop google-login` and sign in as yourself.
  5. **Your Snoop API key:** in the Anthropic Console's `Snoop` workspace, create a key named for you; store it with `security -i` → `add-generic-password -U -s snoop-anthropic -a <your mac username> -w <paste>` → `quit`.
  6. **Your Snoop Chrome profile:** Chrome → Add profile "Snoop" → sign in as yourself → `chrome://extensions` → Developer mode → Load unpacked → `yo-snoop/extension`.
  7. **Each meeting:** `./snoop start`; in the Snoop profile, open the meeting, Join, turn captions on; step away.
  8. **Stopping and updating:** Ctrl-C in the terminal; `git pull` then reload the extension.
  9. **If something's wrong:** the spec §6 failure table, reworded for a person, plus `./snoop doctor`.
- [ ] **Step 2: Mark every command as "verified in Task 2/4"** — each command in the runbook gets checked off when Brett runs it in Task 2 and a second host runs it in Task 4; a command that needed changing is fixed in the runbook the same day.
- [ ] **Step 3: Commit** — `git add docs/RUNBOOK.md && git commit -m "docs: per-host runbook"`

---

### Task 2: Brett's install

- [ ] **Step 1:** Follow `docs/RUNBOOK.md` sections 1–7 on Brett's Mac exactly as written. Record any deviation in the runbook.
- [ ] **Step 2:** `./snoop doctor` → all PASS. Paste the output (no secrets in it) into `docs/rehearsal/phase-1.md` under "Brett install".
- [ ] **Step 3: Commit** — `git add docs && git commit -m "rehearsal: Brett install"`

---

### Task 3: Phase 1 rehearsal (Brett hosts; Jeremy or Lindsay plus one outside account)

**Files:**
- Create: `docs/rehearsal/phase-1.md`

- [ ] **Step 1: Write the checklist with an empty Result column**

| # | Line | Expected | Result (observed) | When (PDT) | By |
|---|---|---|---|---|---|
| R1 | Tile | "Snoop (Brett Evans)" card | | | |
| R2 | Q: "Yo Snoop, how many v1 to v2 gaps are there, and how many are missing?" | correct per the gap map, graded by Brett | | | |
| R3 | Q: "Yo Snoop, how does an accessibility review run in v2?" | correct per `feat/AC-Version-2`, graded | | | |
| R4 | Q: "Yo Snoop, where does multi-model support stand?" | correct per branches/PRs, graded | | | |
| R5 | Q: "Yo Snoop, what does a v2 run cost compared with Beast Mode?" | correct per cost data, graded | | | |
| R6 | Every answer starts "Snoop here" | yes | | | |
| R7 | Long answer | ≤ 3 sentences spoken; full answer in Chat | | | |
| R8 | Gmail account joins mid-answer | speech stops; rest in Chat | | | |
| R9 | Anonymous guest, another-domain account, dial-in (each) | room = mixed; answers to Chat only; spoken "Snoop here, sent it to Chat." | | | |
| R10 | Guest says "peanut butter" | silent until "Yo Snoop"; a running deep dive still posts to Chat | | | |
| R11 | Refresher stopped 31 min | "My notes are 31 minutes old." | | | |
| R12 | Snoop's own speech | never triggers wake or stop | | | |
| R13 | Guest renames to "Jeremy Leeds" and asks | ignored (asker refused) | | | |
| R14 | Question log | one line per question; no other caption text (grep an earlier sentence → 0) | | | |
| R15 | Cost | Console `Snoop` workspace spend for the rehearsal hour, recorded | | | |

- [ ] **Step 2: Run it** — fill every row with what actually happened. Any FAIL on R6, R8–R10, R12 or R13 blocks rollout; fix (with a failing test first, in Plans 1–2's style), rerun that row.
- [ ] **Step 3: Commit** — `git add docs/rehearsal/phase-1.md && git commit -m "rehearsal: Phase 1 results (Brett host)"`

---

### Task 4: Second host's install (Jeremy or Lindsay, on their own Mac)

- [ ] **Step 1:** They follow `docs/RUNBOOK.md` alone; Brett watches, does not type. Every point where they needed help becomes a runbook fix.
- [ ] **Step 2:** `./snoop whoami` → "Snoop (<their name>)".
- [ ] **Step 3: Negative control on their Mac** — after `./snoop doctor` passes, they run `chmod 750 $HOME`, rerun doctor (must FAIL the home and selftest checks), then `chmod 700 $HOME` and rerun (PASS). Record.
- [ ] **Step 4:** Repeat rehearsal rows R1, R2, R6, R8, R12 with them as host. Record under "Second host".
- [ ] **Step 5: Commit** — `git add docs && git commit -m "rehearsal: second host install"`

---

### Task 5: Two Snoops in one meeting (D32), third install, done

- [ ] **Step 1:** The third roster member installs (as Task 4).
- [ ] **Step 2: Two hosts start Snoop in the same meeting.** Someone asks "Yo Snoop, is CI green on main?". Expected: at most one overlapping "Snoop here" (≤ ~1 s), then the lower-priority Snoop posts once to Chat that it stood down; the next question gets exactly one answer. Record.
- [ ] **Step 3: Phase 1 done** — all rows recorded; merge the branch to `main` via a PR in `brett-saasless/yo-snoop`; tag `v0.1.0`; delete leftover keys listed in Plan 0's cleanup log.

```bash
git add docs/rehearsal/phase-1.md
git commit -m "rehearsal: two-Snoop check; Phase 1 complete"
git push
```
