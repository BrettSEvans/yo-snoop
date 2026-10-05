# Snoop: voice standup bot for Saasless Google Meet — design

**Status:** draft for owner review · **Date:** 2026-10-05 · **Owner:** Brett Evans
**Audience:** Saasless team only (Brett, Jeremy, Lindsay). Internal tool; never customer-facing.

## 1. Purpose

Saasless meetings iterate on product ideas against the Agent-C repo, and the
questions asked are about the real system: how a workflow runs in v2 versus v1,
how many v1→v2 gaps remain, what a run costs, where a branch stands. Today those
answers wait until after the meeting (the 2026-10-05 standup notes record Brett
unsure of v2's atomic-workflow mechanics mid-meeting).

Snoop is a bot that joins Saasless Google Meet calls, answers spoken questions
about the Agent-C repo when addressed with "Yo Snoop", and speaks or posts the
answer — without putting repo content on an internet-facing machine or in front
of anyone outside Saasless.

**Success:** in a rehearsal Meet, Snoop answers the acceptance questions in §9
correctly (Brett grades against the repo), never speaks while a non-`saasless.ai`
participant is present, and passes every negative control in §9.

## 2. Decisions (owner, 2026-10-05)

| # | Decision |
|---|---|
| D1 | IP-safe first. Security constraints win over convenience. |
| D2 | Participants: Brett, Jeremy, Lindsay, all on `saasless.ai`. |
| D3 | Hybrid: cloud VM is ears and mouth only; the brain runs on team Macs. |
| D4 | Any participant whose account is not `saasless.ai` (gmail, other company, anonymous, dial-in) makes the room **mixed**. |
| D5 | Mixed room: only brett@, jeremy@, lindsay@startup.ai may ask; answers go to Google Chat, never spoken. |
| D6 | "Peanut butter" from anyone mutes speech until "Yo Snoop" is said again. It does not cancel research or Chat posts. |
| D7 | Wake phrase is "Yo Snoop". |
| D8 | Speech via Meet captions in, Google Cloud TTS out (approach A); self-hosted Whisper is the fallback (B). Deepgram/ElevenLabs rejected: new vendors hearing all audio. |
| D9 | One fixed Google Chat space with the three team members; answers @-mention the asker. |
| D10 | Bot joins as a dedicated `agent-c@startup.ai` Workspace account. |
| D11 | Voice character: the `snoop` output style (`~/.claude/output-styles/snoop.md`), curse words off. Stock Google voice — no imitation of Snoop Dogg's real voice. |
| D12 | "Ask the repo anything": the brain reads the full repo (code, docs, all branches), not a curated snapshot. |
| D13 | Brain may run on Brett's, Jeremy's or Lindsay's Mac. |
| D14 | Code lives in a separate private repo, `brett-saasless/yo-snoop`, never in Agent-C (Agent-C's customer export ships all of `scripts/`). |
| D15 | v1 brain on Brett's Mac uses registry-mcp read tools. **v2 requirement:** registry-mcp works on Jeremy's and Lindsay's Macs. |
| D16 | Owner's macOS home is set to `700` by the installer. |
| D17 | Snoop's Google account communicates only by speaking in a meeting when allowed and by Chat to Brett, Jeremy and Lindsay. |
| D18 | Spoken answers: 3 sentences, then ask the room if they want more and on what; continue in ~75 s chunks that end on a complete thought, asking again after each. |
| D19 | v2 direction: Snoop's own MCP server reading a Google Drive folder for the meeting (code or document sets), not only the Agent-C repo. Out of v1. §7.1. |

## 3. Components

```
 Google Meet ──captions──▶ [VM] Attendee ──▶ [VM] Conductor ──question──▶ [Mac] Brain
      ▲                          ▲                 │   ▲                      │
      └──── Google TTS audio ────┘                 │   └──────── answer ──────┘
                                                   ▼
                                   [VM] Chat poster ──▶ team Chat space
```

### 3.1 Cloud VM — ears and mouth; holds no repo, snapshot or IP

1. **Attendee** (self-hosted, pinned version; Elastic License 2.0 — internal use
   permitted). Joins Meet as `agent-c@startup.ai`, transcribes from Meet's own
   closed captions (`meeting_closed_captions` provider), speaks via its built-in
   Google TTS.
2. **Conductor** (our code). Wake/stop detection, room check, asker check,
   delivery choice, brain routing. §4.
3. **Chat poster.** Google Chat app (service account, `chat.bot` scope). Posts
   only to the one configured space ID; any other destination is refused in code.

**VM credentials:** bot Google sign-in (SAML, via Attendee), Meet read-only scope
for the participant check, Chat app service account, Google TTS service account,
per-Mac brain connection keys. **No Anthropic key. No GitHub token.**

### 3.2 Team Macs — the brain (same installer on all three)

4. **Brain connector.** Dials **out** to the VM over an authenticated, encrypted
   connection; no inbound port on any laptop. One revocable credential per Mac.
5. **Sandboxed Claude Code (headless)**, run as macOS user `snoop`. §5.
6. **Knowledge refresher.** Fetches the `snoop` user's read-only Agent-C clone
   (all branches) before each meeting. On Brett's Mac it also builds the
   `AGENT_C_HOME` bundle (§5.2).

**Routing:** the VM uses the first connected brain in the order Brett → Jeremy →
Lindsay. None online → Snoop says "no brain online".

**Mac credentials** (held by `snoop` only): fetch-only GitHub deploy key; a
dedicated Anthropic API key in its own Console workspace with a monthly spend limit.

### 3.3 Google Workspace setup for `agent-c@startup.ai`

- Own organizational unit. The Attendee SAML SSO profile is assigned to **that
  OU only** — if it covered more, a leaked signing key could sign in as Brett.
- Services on: Meet; Chat (receiving membership in the one space only);
  Calendar **read-only, RSVP replies off** (the Conductor reads its invites to
  know which meetings to join).
- Services off: Gmail, Drive, Docs, and everything else.
- Meet in-meeting chat: Snoop never posts there (D17).
- Invited only to meetings the team chooses.

## 4. Conversation flow

1. **Caption arrives** from Attendee with the speaker's display name.
2. **Stop check, every line, first.** "Peanut butter" from anyone: cut audio now,
   enter **muted**. Muted ignores everything except the wake phrase. Research in
   flight continues; finished answers still post to Chat (D6).
3. **Wake check.** Utterance *starts with* "Yo Snoop" or a caption variant
   ("you Snoop", "yo, Snoopy"). Mid-sentence mentions never trigger. Question
   ends after ~1.5 s of speaker silence. A valid wake also clears muted.
4. **Room check.** Meet REST participants for this conference, excluding the bot
   by its user ID. Each signed-in participant resolved against the `saasless.ai`
   directory. Any anonymous, dial-in, or non-`saasless.ai` participant → mixed.
   **API error or timeout → mixed** (fail closed).
5. **Asker check.** Speaker display name must match exactly one verified
   `saasless.ai` participant. Duplicate names, or a name matching a non-team
   record → ignored. Mixed room: asker must also be brett@, jeremy@ or lindsay@.
6. **Route to brain.** Question + room verdict sent to the routed Mac.
7. **Deliver.**
   - All-team room: speak per the pacing rule below. Deep dives (>~5 s): say
     "lemme dig in the repo", post the answer to Chat when ready.
   - Mixed room: post to Chat @-mentioning the asker; speak only "sent it to Chat".
8. **Re-check before every spoken sentence.** If the room has turned mixed, stop
   speaking and post the remainder to Chat.

**Pacing rule (D18).** Applies to every spoken answer.

1. **Opening:** at most 3 sentences.
2. **Check-in:** if more remains, ask the room "want more? on what?" and listen
   ~8 s. Any participant allowed to ask (§4 step 5) can reply, without the wake
   phrase:
   - "yes" / "go on" → next chunk.
   - A focus ("more on the cost part") → treated as a follow-up question;
     the next chunk answers that.
   - "no", or silence → stop speaking.
3. **Chunks:** ~75 s of speech each (about 190 words), approximate. A chunk
   always ends at the end of a complete thought, never mid-sentence or
   mid-point: the brain returns the answer as ordered self-contained points,
   and the Conductor cuts only between points, letting a chunk run past 75 s
   rather than split a point. After each chunk, check in again (step 2).
4. **Nothing is lost:** whenever an answer stops before its end — declined,
   silence, "peanut butter", room turned mixed — the full answer posts to Chat.
5. "Peanut butter" and the per-sentence room re-check override pacing at all times.

**Persona:** system prompt carries `snoop.md` with two meeting overrides: curse
words off; the "identifiers written straight" rule applies to Chat text only.
Target: first spoken word ~3 s after the question ends (snapshot-style
questions); deep dives 15–60 s.

## 5. Brain sandbox and answer gate

### 5.1 User isolation — the real wall

- Installer creates `snoop` as a standard (non-admin) user and sets the owner's
  home to `700`. Measured on Brett's Mac 2026-10-05: home was `drwxr-x---`
  group `staff`, and `~/.claude`, `~/.agent-c`, `~/Code` were `drwxr-xr-x` — a
  default new user (group `staff`) could read all of them.
- **Negative control, every install, every Mac:** as `snoop`, attempt to read
  `~/.claude/settings.json`, `~/.agent-c/registry.json`, and a file under
  `~/Code`. Any success aborts the install.
- Keychain is per-user; `snoop` cannot reach the owner's.

### 5.2 What the brain reads

- Its own Agent-C clone, all branches, fetch-only.
- **Brett's Mac only (v1):** an `AGENT_C_HOME` bundle — a copy of `~/.agent-c`
  with project paths rewritten to `snoop`'s clones — and registry-mcp started
  against it. Built as a self-contained bundle so v2 only has to transport it
  to Jeremy's and Lindsay's Macs (D15).
- Questions on Jeremy's/Lindsay's brain that need registry state get "that's on
  Brett's machine" in v1.

### 5.3 Claude Code configuration (installer-owned, not writable by `snoop`)

- **Allow:** `Read`, `Grep`, `Glob`; `git log`, `git show`, `git diff`,
  `git branch`; registry-mcp (Brett only): `registry_list`, `registry_get`,
  `stage_get`, `stage_diagnose`, `backlog_list`, `backlog_get`,
  `history_events`, `history_metrics`, `server_info`.
- **Deny:** everything else — `Write`, `Edit`, web tools, sub-agents, other
  shell, every other registry-mcp tool (registry-mcp has no read-only mode).
  Unlisted tools are denied, never prompted; bypass mode never used.
- **Second net:** registry-mcp runs against the disposable bundle, so a write
  that slipped through changes a copy, never the real registry.
- **Limits:** 15 turns and 90 s per question. Model is a config value, starting
  at Sonnet 5.5. Monthly cap enforced by the Console workspace limit.
- **Known soft spot:** some `git` flags write files (e.g. `--output`). `snoop`
  can only write in its own home, which is why 5.1 is the wall.

### 5.4 Answer gate (on the Mac, before an answer leaves)

- Secret scan (patterns from Agent-C `scripts/agent-c-export-audit.js` plus key
  formats: Anthropic, GitHub, AWS, private keys). **Any hit blocks the whole
  answer** → "can't share that one". Scanner crash also blocks.
- No IP-term filter: answers reach team members only (D5, D17).

### 5.5 Logs

Per question, on the answering Mac: question, room verdict, answer, tools used,
cost, latency. Kept 7 days. No meeting transcript storage beyond this.

## 6. Failure modes

| Failure | Behavior |
|---|---|
| No brain online | "no brain online" |
| Mac sleeps mid-question | 90 s timeout → "lost my brain, ask again" |
| Participant API error/slow | room treated as mixed |
| Captions miss the wake phrase | nothing (fails quiet) |
| Clone refresh fails | answers from the old clone and states its age |
| Answer gate hit | "can't share that one" |
| Monthly spend limit hit | "out of budget for the month" |
| Meet UI change breaks Attendee | pinned version; upgrade deliberately |
| SAML signing key leaks | rotate; OU scoping limits the account to Meet + Chat |

## 7. Non-goals (v1)

- Customer-facing use of any kind (owner decision; also required by ELv2).
- Writes by voice: no tickets, approvals, or code changes.
- Unprompted interjection.
- registry-mcp on Jeremy's and Lindsay's Macs (v2, D15).
- Imitating Snoop Dogg's real voice.
- Zoom, Teams, or meetings Snoop was not invited to.
- Any communication from `agent-c@` other than meeting speech and team Chat.
- Knowledge sources other than the Agent-C repo and registry (v2, §7.1).

### 7.1 v2 direction: per-meeting Google Drive knowledge (D19)

Not designed yet; recorded so v1 does not block it.

- **Shape:** Snoop exposes its own MCP server to the brain, with read-only tools
  over one Drive folder chosen per meeting (code or documents). A natural
  default is the folder or files attached to the meeting's calendar event.
- **v1 must not block it:** the brain's knowledge sources are a list in config,
  not hard-coded to the Agent-C clone; the allow-list in §5.3 is generated from
  that list.
- **Open questions for the v2 design:**
  - **Identity.** D17 and §3.3 turn Drive off for `agent-c@`. Reading Drive needs
    either Drive on with Viewer-only sharing per folder, or a separate
    read-only principal. Changes the account's blast radius.
  - **Prompt injection from documents.** A shared doc can contain text aimed at
    Snoop. Read-only tools and the answer gate limit damage; answer steering
    is not prevented.
  - **Who may point Snoop at a folder**, and whether outsiders' shared files are
    ever eligible.
  - **Product vs internal.** Value as a product conflicts with v1's
    internal-only rule and with Attendee's ELv2 (no hosted service to third
    parties). A product version needs its own meeting-bot layer or a
    commercial license, and its own security review.

## 8. Unverified — confirm before the implementation plan

1. Which principal the Meet REST participants call needs (organizer token vs the
   bot's own account) and its live polling latency.
2. Meet caption latency and accuracy for the wake phrase in practice.
3. Exact headless Claude Code flags/settings for the allow/deny lists in 5.3
   (probe the real signature before relying on it).
4. Attendee SAML SSO setup against a Workspace OU-scoped profile.
5. Google Chat app restricted to one space and three users at the Workspace level.

Verified 2026-10-05: Attendee supports Meet captions transcription and Google TTS
output (source); Meet Media API is receive-only (Google docs); Attendee license
is ELv2; registry-mcp has no read-only mode and honors `AGENT_C_HOME`.

## 9. Testing and acceptance

**Unit (fixtures):** wake matcher (variants; mid-sentence no-trigger); stop →
muted → wake re-arm; room classifier (all-team, anonymous, dial-in, gmail,
other-domain, API error → mixed); asker matcher (duplicates, renamed outsider);
brain routing order; Chat poster refuses any non-configured space.

**Sandbox (each Mac):** 5.1 negative control; a prompt to write a file is
refused; a registry-mcp write tool is refused and a before/after hash shows the
real `~/.agent-c` unchanged; a planted fake key is blocked by the answer gate.

**End-to-end rehearsal** (test Meet, `agent-c@` + two team accounts):
- Acceptance questions from the 2026-10-05 standup, graded by Brett:
  - How many v1→v2 gaps are there, and how many are missing?
  - How does an accessibility-review workflow run in v2?
  - Where does multi-model support (Cursor, Gemini, OpenAI) stand?
  - What does a v2 run cost compared with Beast Mode?
- A non-`saasless.ai` participant of each kind (gmail, other domain, anonymous,
  dial-in) joins mid-answer: speech stops; the remainder posts to Chat.
- Any participant says "peanut butter": Snoop stays silent until "Yo Snoop";
  an in-flight deep dive still posts to Chat.
- Pacing: a long answer stops after 3 sentences and asks; "yes" yields a chunk
  of roughly 75 s that ends on a complete point; a focused reply redirects the
  next chunk; silence stops speech and the full answer is in Chat.
