# Snoop: voice bot for Saasless Google Meet meetings — design

**Status:** approved 2026-10-05; **revised 2026-10-06** (Chrome-profile approach D26–D30; any-host roster D31–D32) · **Owner:** Brett Evans
**Audience:** Saasless team only — the members listed in the team roster (D31), today Brett, Jeremy, Lindsay. Internal tool; never customer-facing.

## 1. Purpose

Saasless meetings iterate on product ideas against the Agent-C repo, and the
questions asked are about the real system: how a workflow runs in v2 versus v1,
how many v1→v2 gaps remain, what a run costs, where a branch stands. Today those
answers wait until after the meeting (the 2026-10-05 standup notes record Brett
unsure of v2's atomic-workflow mechanics mid-meeting).

Snoop takes a team member's seat (the **host**) in Saasless Google Meet calls, answers spoken questions
about the Agent-C repo when addressed with "Yo Snoop", and speaks or posts the
answer — without putting repo content on an internet-facing machine or in front
of anyone outside Saasless.

**Success:** in a rehearsal Meet, Snoop answers the acceptance questions in §9
correctly (Brett grades against the repo), never speaks while a non-`saasless.ai`
participant is present, and passes every negative control in §9.

## 2. Decisions (owner)

| # | Decision |
|---|---|
| D1 | IP-safe first. Security constraints win over convenience. |
| D2 | Team: the members in the roster (D31), all on `saasless.ai`; today Brett, Jeremy, Lindsay. |
| D3 | ~~Hybrid cloud VM + Mac brain.~~ **Superseded by D26** (2026-10-06): everything runs on the host's Mac; no VM. |
| D4 | Any participant whose account is not `saasless.ai` (gmail, other company, anonymous, dial-in) makes the room **mixed**. |
| D5 | Mixed room: only roster members marked `mixed_room_asker` (today brett@, jeremy@, lindsay@) may ask; answers go to Google Chat, never spoken. |
| D6 | "Peanut butter" from anyone mutes speech until "Yo Snoop" is said again. It does not cancel research or Chat posts. |
| D7 | Wake phrase is "Yo Snoop". |
| D8 | Speech in: Meet's own live captions, read from the Meet page by the Snoop extension (D27). Speech out: Google Cloud TTS. Fallback for input: self-hosted Whisper. Deepgram/ElevenLabs rejected: new vendors hearing all audio. |
| D9 | One fixed Google Chat space whose members are the roster's Google Group; answers @-mention the asker. |
| D10 | ~~Dedicated `agent-c@startup.ai` account.~~ **Superseded by D26** (2026-10-06): no bot account; Snoop sits in the host's own seat. |
| D11 | Voice character: the `snoop` output style (`~/.claude/output-styles/snoop.md`), curse words off. Stock Google voice — no imitation of Snoop Dogg's real voice. |
| D12 | "Ask the repo anything": the brain reads the full repo (code, docs, all branches), not a curated snapshot. |
| D13 | **v1 supports any roster member as host**, on their own Mac, Google account and Snoop API key; the card names the host ("Snoop (Jeremy Leeds)"). Rollout order: Brett's Mac passes rehearsal first, then Jeremy's and Lindsay's installs. Two Snoops in one meeting are resolved by D32. |
| D14 | Code lives in a separate private repo, `brett-saasless/yo-snoop`, never in Agent-C (Agent-C's customer export ships all of `scripts/`). |
| D15 | v1: only Brett's Mac has the live registry, so only a Brett-hosted Snoop uses registry-mcp read tools; on other hosts Snoop says "that's on Brett's machine". **v2 requirement:** registry-mcp works on every host's Mac. |
| D16 | Owner's macOS home is set to `700` by the installer. |
| D17 | Snoop communicates only by speaking in a meeting when allowed and by Chat to the team space. The extension never sends Meet chat, email, or anything else from the host's account. |
| D18 | Spoken answers: 3 sentences, then ask the room if they want more and on what; continue in ~75 s chunks that end on a complete thought, asking again after each. |
| D19 | v2 direction: Snoop's own MCP server reading a Google Drive folder for the meeting (code or document sets), not only the Agent-C repo. Out of v1. §7.1. |
| D20 | v1 uses Pipecat (Conductor pipeline), repomix (repo map) and Serena (code navigation). Each one's speed is re-measured in rehearsal before it is relied on. |
| D21 | Serena's editing tools are removed before it is added (§5.3.1). |
| D22 | Pre-loading in v1: listen to all-team meetings, spot topics, pre-load answers' material into one per-meeting brain session. Memory only; mixed rooms pause it. §4. |
| D23 | Keep the clone: refreshed every 5 min during meetings, plus a PR/CI status file; refresher runs as the owner so `snoop` holds no GitHub credential. §3.2. |
| D24 | Snoop joins any Saasless meeting the host is invited to, organized by any roster member — not only standup. |
| D25 | Development and testing (Plans 0–2) may run on the owner's own Claude subscription (Max/Team), as the owner, on the owner's Mac. The team-facing Snoop runs on an API key (§3.2), per Anthropic's guidance that shared production automation uses an API key; a subscription credential is never placed where the `snoop` user can read it. |
| D26 | **Chrome-profile approach (2026-10-06):** Snoop takes the host's own seat. The host signs in to Google themselves in a dedicated Chrome profile used only for Snoop; Snoop never handles the host's password and never signs in as them. No VM, no Attendee, no extra Google account. Rejected alternative: SAML sign-in of a bot as brett@ (would let a signing key sign in as Brett everywhere). |
| D27 | A Snoop Chrome extension, loaded unpacked only in that profile, reads Meet's captions and speaker names, supplies Snoop's voice, and shows the video card. Host permission `https://meet.google.com/*` only. |
| D28 | Disclosure: Snoop's camera tile is a card reading **"Snoop (<host display name>)"** — e.g. "Snoop (Brett Evans)", "Snoop (Jeremy Leeds)" — from the roster, and every spoken answer starts with **"Snoop here"**. The spoken label is mandatory even if the card fails. The Google account name is never changed. |
| D29 | Snoop's voice reaches Meet through the extension (supplying the tab's microphone); fallback is the BlackHole virtual audio device. Chosen by Plan 0 probe. |
| D30 | Snoop ignores captions of its own speech (labeled as the host's own seat) so it never reacts to itself. |
| D31 | **Team roster** (2026-10-06): one file, `config/team.json` in this repo, lists every member — email, display name, host priority, `may_host`, `mixed_room_asker`. Adding a person is a roster change plus adding them to the Google Group `snoop-team@startup.ai` (Chat space membership and Chat app visibility follow the group) and running the installer on their Mac. No code names a person. |
| D32 | **One Snoop per meeting** (2026-10-06): a Snoop that hears another seat's caption beginning "Snoop here" compares roster host priority; the lower-priority Snoop goes passive for the rest of the meeting (no speech, no Chat answers) and posts once to Chat that it stood down. Worst case both speak for about a second on the first answer. Team habit: one host per meeting. |
| D33 | **Phasing (2026-10-06):** **Phase 1 — first working Snoop, target ~1 week**, runnable by any roster member on their own Mac: Chrome-profile seat + extension (captions, voice, card), wake / peanut-butter mute, room + asker checks, Chat delivery, D32 one-Snoop guard, sandboxed brain (clone, PR/CI file, repo map, read-only Serena; registry-mcp on Brett's Mac), answer gate, per-host installer. Spoken answers are at most 3 sentences, with anything longer posted in full to Chat. **Phase 2:** pre-loading (D22) and the 75-second pacing check-ins (D18 steps 2–3). |

## 3. Components

```
                       Host's Mac
 ┌───────────────────────────────────────────────────────────────────────┐
 │  Chrome profile "Snoop" (host signs in as themselves)                 │
 │   Meet tab ◀── Snoop extension: captions out · voice + card in        │
 │                      │  ▲  localhost websocket (127.0.0.1, token)     │
 │                      ▼  │                                             │
 │  Conductor (owner) ── question ──▶ Brain (macOS user `snoop`)         │
 │     │  ▲  room check (Meet REST)        │ read-only clone, repo map,  │
 │     │  └────────── answer ◀── gate ─────┘ registry bundle, Serena     │
 │     ▼                                                                 │
 │  Chat poster ──▶ team Chat space        Google TTS ──▶ voice          │
 └───────────────────────────────────────────────────────────────────────┘
```

### 3.1 The meeting seat (host's Mac, owner side)

1. **Chrome profile "Snoop".** A dedicated profile the host signs in to as
   themselves, used only for Snoop meetings. In v1 the host opens the meeting
   link in it and clicks Join; Snoop then holds the seat and the host can step
   away. Captions are turned on in that tab.
2. **Snoop extension (D27).** Manifest V3, unpacked, never published.
   - Host permission `https://meet.google.com/*` only. No `tabs`, `cookies`,
     `identity`, `history`, `downloads`, or other-site access.
   - Reads caption lines and speaker names from the Meet page and sends them to
     the Conductor over a localhost websocket (`127.0.0.1` only, per-install
     token).
   - Supplies Snoop's voice as the tab's microphone (D29) and the
     "Snoop (<host display name>)" card from the roster as the tab's camera (D28), by providing those
     media streams to the Meet page. If the probe shows voice injection is
     unreliable, voice goes through BlackHole instead (Chrome mic set to
     BlackHole in that profile).
   - Never clicks, types or sends anything in Meet except: turning captions on,
     and, if ever automated, Join. Never sends Meet chat (D17).
3. **Conductor** (our code, built on [Pipecat](https://github.com/pipecat-ai/pipecat),
   BSD-2, D20), runs as the **owner**. Wake/stop detection, room check, asker
   check, delivery choice, pacing, pre-loading. §4. Streams the brain's answer
   sentence by sentence into Google TTS and on to the extension, so the first
   word does not wait for the whole answer; handles the "peanut butter" cut.
4. **Chat poster.** Google Chat app (service account, `chat.bot` scope), run by
   the Conductor. Posts only to the one configured space ID; any other
   destination is refused in code.

**Owner-side credentials** (never readable by `snoop`): the host's read-only
Meet token (`meetings.space.readonly`, for the room check), the Chat app
service-account key, the Google TTS service-account key, the extension's
localhost token. The host's Google password and session stay inside Chrome;
Snoop's code never reads Chrome's cookies or storage.

### 3.2 The brain (same Mac, sandboxed)

5. **Sandboxed Claude Code (headless, via the Agent SDK)**, run as macOS user
   `snoop`, reached by the Conductor over a local socket. §5.
6. **Knowledge refresher (D23).** Runs as the **Mac's owner** (launchd), not as
   `snoop`, so `snoop` holds no GitHub credential at all. Writes into a
   directory `snoop` can read but not write. Fetches the Agent-C clone (all
   branches) before each meeting and **every 5 minutes during one**, and writes
   a **PR/CI status file** (open and recently merged PRs, review state, latest
   CI result per branch) from the GitHub API, so the model gets that data with
   no network access of its own. Snoop states the clone's age when it answers.
   Unpushed work is invisible by design; push a WIP branch to show it to Snoop.
   On Brett's Mac it also builds the `AGENT_C_HOME` bundle (§5.2). It also
   builds the **repo map** with [repomix](https://github.com/yamadashy/repomix)
   (MIT, D20): a compressed, single-file view of the clone, loaded as the brain
   session's cached prefix. Size budget and include filters are set in the plan
   (Agent-C is too large to pack whole). repomix's built-in secret check runs,
   and the §5.4 secret scan runs on the map too; a hit blocks the map, not the
   meeting.

**`snoop` credentials:** in production, a dedicated Anthropic API key in its own
Console workspace with a monthly spend limit, supplied through Claude Code's key
helper from `snoop`'s login Keychain, never a plain file (D25). Read deny rules
cover `snoop`'s config and credential paths; the §5.4 secret scan is the
backstop. Owner-side GitHub credentials: fetch-only deploy key and a
fine-grained read-only token (pull requests: read, actions: read, metadata).

### 3.3 Google setup (no new account, no new seat)

- **Google Cloud project `yo-snoop`** (no Workspace seat): Meet REST API, Chat
  API, People API, Cloud Text-to-Speech API; OAuth consent **Internal**; one
  Desktop OAuth client for the host's read-only Meet token; service accounts for
  Chat and TTS.
- **Google Group `snoop-team@startup.ai`** (free) holds the roster's members.
- **Chat app** visible to that group only; the one `Snoop` space's members are
  that group. Adding a person to the group grants both.
- **Per-host keys:** each host's Mac gets its own Chat and TTS service-account
  keys and its own Snoop API key (one shared Console workspace, one spend cap),
  each revocable on its own.
- **Host account:** unchanged. Its display name is never changed (D28).

## 4. Conversation flow

1. **Caption arrives** from the extension with the speaker's display name.
   Lines from the host's own seat (Snoop's own voice) are dropped (D30).
2. **Stop check, every line, first.** "Peanut butter" from anyone: cut audio now,
   enter **muted**. Muted ignores everything except the wake phrase. Research in
   flight continues; finished answers still post to Chat (D6).
3. **Wake check.** Utterance *starts with* "Yo Snoop" or a caption variant
   ("you Snoop", "yo, Snoopy"). Mid-sentence mentions never trigger. Question
   ends after ~1.5 s of speaker silence. A valid wake also clears muted.
4. **Room check.** Meet REST participants for this conference, read with the
   host's read-only token. Snoop's own seat is the host's user ID. Each
   signed-in participant resolved against the `saasless.ai` directory. Any
   anonymous, dial-in, or non-`saasless.ai` participant → mixed.
   **API error or timeout → mixed** (fail closed).
5. **Asker check.** Speaker display name must match exactly one verified
   `saasless.ai` participant. Duplicate names, or a name matching a non-team
   record → ignored. Mixed room: asker must also be a roster `mixed_room_asker`.
   (If the real host also joins from another device, that seat is the same
   account and counts as team.)
6. **Ask the brain.** Question + room verdict go to the brain on the same Mac.
7. **Deliver.**
   - All-team room: speak per the pacing rule below, starting with "Snoop here"
     (D28). Deep dives (>~5 s): say "Snoop here, lemme dig in the repo", post
     the answer to Chat when ready.
   - Mixed room: post to Chat @-mentioning the asker; speak only "Snoop here,
     sent it to Chat".
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
questions); deep dives 15–60 s, less when pre-loaded (measured in rehearsal).

**Pre-loading (D22).** Snoop listens to the whole meeting, not just questions,
so answers start warm.

1. **Rolling transcript:** the last ~5 min of captions, **in the Conductor's
   memory only**, never written to disk or logs.
2. **Topic spotting:** every ~30 s or on a subject change, a fast model (Haiku
   4.5) extracts topics, ticket IDs, branch and file names from the window.
3. **Pre-load:** the brain looks those up with its normal read-only tools.
4. **One brain session per meeting:** a single headless Claude Code session
   stays open for the meeting, starting from the repo map, accumulating
   pre-loaded material, and reused by every question (prompt caching keeps it
   fast and cheap). Follow-ups like "what did *that* cost?" resolve from it.
5. **All-team rooms only:** the moment the room is mixed — or the participant
   check fails — topic spotting stops and outsiders' speech is never sent
   anywhere. It resumes when the room is all-team again.
6. **Prepares, never speaks:** speech still needs "Yo Snoop". "Peanut butter"
   mutes speech but does not stop pre-loading.
7. **Out of v1:** pre-drafting answers to guessed questions.
8. **Team notice:** every roster member is told, before first use, that Snoop
   hears the whole all-team meeting, not only wake-phrase questions, and that
   it sits in the host's seat.

Pre-loading counts against the same monthly spend limit; its cost per meeting
hour is measured in rehearsal.

## 5. Brain sandbox and answer gate

### 5.1 User isolation — the real wall

- Installer creates `snoop` as a standard (non-admin) user and sets the owner's
  home to `700`. Measured on Brett's Mac 2026-10-05: home was `drwxr-x---`
  group `staff`, and `~/.claude`, `~/.agent-c`, `~/Code` were `drwxr-xr-x` — a
  default new user (group `staff`) could read all of them.
- **Negative control, every install:** as `snoop`, attempt to read
  `~/.claude/settings.json`, `~/.agent-c/registry.json`, a file under `~/Code`,
  and the Chrome profile directory under `~/Library/Application Support/Google/Chrome`.
  Any success aborts the install.
- Keychain is per-user; `snoop` cannot reach the owner's.

### 5.2 What the brain reads

- The Agent-C clone (all branches), the PR/CI status file and the repo map, all
  written by the owner's refresher into a directory `snoop` can read but not
  write (§3.2, D23).
- **Brett's Mac only (v1):** an `AGENT_C_HOME` bundle — a copy of `~/.agent-c`
  with project paths rewritten to `snoop`'s clones — and registry-mcp started
  against it. Built as a self-contained bundle so v2 only has to transport it
  to Jeremy's and Lindsay's Macs (D15).

### 5.3 Claude Code configuration (installer-owned, not writable by `snoop`)

- **Allow:** `Read`, `Grep`, `Glob`; `git log`, `git show`, `git diff`,
  `git branch`; registry-mcp (Brett only): `registry_list`, `registry_get`,
  `stage_get`, `stage_diagnose`, `backlog_list`, `backlog_get`,
  `history_events`, `history_metrics`, `server_info`.
- **Deny:** everything else — `Write`, `Edit`, web tools, sub-agents, other
  shell, every other registry-mcp tool (registry-mcp has no read-only mode).
  Unlisted tools are denied, never prompted (`permission_mode="dontAsk"`);
  bypass mode never used. No owner settings, hooks or MCP servers load
  (`setting_sources=[]`, `strict_mcp_config=True`; P3).
- **Second net:** registry-mcp runs against the disposable bundle, so a write
  that slipped through changes a copy, never the real registry.
- **Limits:** 15 turns and 90 s per question (SDK `max_turns`; the CLI has no
  `--max-turns`, P3). Model is a config value, starting at Sonnet 5.5. Monthly
  cap enforced by the Console workspace limit.
- **Known soft spot:** some `git` flags write files (e.g. `--output`). `snoop`
  can only write in its own home, which is why 5.1 is the wall.

### 5.3.1 Serena, editing tools removed (D20, D21)

[Serena](https://github.com/oraios/serena) (GPL-3.0; internal use) gives the
brain symbol-level code navigation. Its editing, shell, memory-write and
project-switching tools are **removed before it is added**, in three
independent layers:

1. **Serena's own config** (installer-owned, not writable by `snoop`):
   `read_only: true` in the project definition, plus `excluded_tools` listing
   every tool not in the keep list below. Serena's web dashboard is disabled.
   The project is fixed at launch; no project switching.
2. **Claude Code allow-list** names only the kept Serena tools (5.3 rules apply:
   anything unlisted is denied).
3. **Startup assertion:** before a meeting, the brain lists the tools Serena
   actually exposes and **refuses to start** if any tool outside the keep list
   is present. Reason: Serena's changelog records a bug (#1938) where
   `read_only` was not applied to the base tool set in single-project context.
   Serena is pinned to a version after that fix and upgraded deliberately.

**Keep (read-only),** from Serena's source 2026-10-05: `read_file`, `list_dir`,
`find_file`, `search_for_pattern`, `get_symbols_overview`, `find_symbol`,
`find_referencing_symbols`, `find_implementations`, `find_declaration`,
`get_diagnostics_for_file`, `get_diagnostics_for_symbol`, `read_memory`,
`list_memories`.

**Removed:** all file editing (`create_text_file`, `replace_content`,
`replace_in_files`, `delete_lines`, `replace_lines`, `insert_at_line`); all
symbol editing (`replace_symbol_body`, `insert_after_symbol`,
`insert_before_symbol`, `rename_symbol`); memory writes (`write_memory`,
`delete_memory`, `rename_memory`, `edit_memory`, `onboarding`);
`execute_shell_command`; `serena_repl` (code execution); `open_dashboard`;
`activate_project`, `remove_project`, `query_project`,
`list_queryable_projects`; `restart_language_server`.
Exact tool names are confirmed against the pinned version's live tool list in
the plan (class names above map to these snake-case names).

### 5.4 Answer gate (Conductor, before an answer leaves the Mac)

- Secret scan (patterns from Agent-C `scripts/agent-c-export-audit.js` plus key
  formats: Anthropic, GitHub, AWS, Google service-account, private keys).
  **Any hit blocks the whole answer** → "Snoop here, can't share that one".
  Scanner crash also blocks.
- No IP-term filter: answers reach team members only (D5, D17).

### 5.5 Logs

Per question, on the host's Mac: question, room verdict, answer, tools used,
cost, latency. Kept 7 days. Pre-loading logs topics and lookups only, never
transcript text. No meeting transcript storage anywhere.

## 6. Failure modes

| Failure | Behavior |
|---|---|
| Host's Mac sleeps or Chrome closes | Snoop leaves the meeting; Conductor posts "Snoop dropped" to Chat when it can |
| Brain process down | "Snoop here, my brain's offline" |
| Question exceeds 90 s | "Snoop here, lost the thread, ask again" |
| Participant API error/slow | room treated as mixed |
| Captions off or miss the wake phrase | nothing (fails quiet); extension re-enables captions |
| Meet page change breaks caption reading | extension reports "no captions for 60 s" to the Conductor, which posts a Chat warning; fix and reload |
| Voice injection fails | fall back to BlackHole (D29); spoken label still required |
| Camera card fails | meeting continues; spoken "Snoop here" is the disclosure (D28) |
| Clone refresh fails | answers from the old clone and states its age |
| Answer gate hit | "Snoop here, can't share that one" |
| Monthly spend limit hit | "Snoop here, out of budget for the month" |

## 7. Non-goals (v1)

- Customer-facing use of any kind (owner decision).
- Writes by voice: no tickets, approvals, or code changes.
- Unprompted interjection.
- registry-mcp on Jeremy's and Lindsay's Macs (v2, D15).
- Imitating Snoop Dogg's real voice.
- Zoom, Teams, or meetings the host is not invited to.
- Any action from the host's account other than meeting speech, the camera card,
  turning captions on, and team Chat via the Chat app (D17).
- Auto-joining meetings from the calendar (v1: the host opens the link).
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
  - **Identity.** Reading Drive through the host's own account gives the brain
    the host's whole Drive. Needs a narrow read-only principal or per-folder
    export instead.
  - **Prompt injection from documents.** A shared doc can contain text aimed at
    Snoop. Read-only tools and the answer gate limit damage; answer steering
    is not prevented.
  - **Who may point Snoop at a folder**, and whether outsiders' shared files are
    ever eligible.
  - **Product vs internal.** A product version needs a meeting-bot layer that
    does not sit in a customer's own seat, and its own security review.

## 8. Unverified — confirm before Plans 1–2 (Plan 0)

1. Which principal the Meet REST participants call needs (organizer token vs a
   participant's own token) and its live polling latency. With D26 the host's
   token is used, so a meeting organized by Jeremy or Lindsay must be tested
   with Brett as a non-organizer participant.
2. Caption reading from the Meet page: latency and accuracy for the wake phrase,
   and reliable speaker names.
3. ~~Headless Claude Code controls~~ — **mostly verified** in P3 (2026-10-05);
   key helper deferred to Plan 1 (D25).
4. Extension media: can the extension supply the tab's microphone (Snoop's
   voice) and camera (the card) to Meet reliably; and how fast speech stops.
   BlackHole fallback measured the same way.
5. Google Chat app restricted to one space and three users.
6. Own-voice exclusion (D30): how Meet labels the host's own captions, so
   Snoop never reacts to itself.
7. Two-Snoop detection (D32): another seat's "Snoop here" appears in captions
   with that seat's name, fast enough for the stand-down rule.

Verified 2026-10-05: Meet Media API is receive-only (Google docs); registry-mcp
has no read-only mode and honors `AGENT_C_HOME`; Serena has `read_only` and
`excluded_tools` settings and its tool classes are as listed in §5.3.1; Pipecat
(BSD-2), repomix (MIT) and Serena (GPL-3.0) were all pushed within the last 3
months. P3: sandbox controls hold with positive and negative controls; one SDK
session carries context and serves the cached prefix (second answer 0.97 s).

**Considered and not in v1:** Attendee (self-hosted Meet bot; needs its own
account and SAML sign-in — dropped by D26); faster-whisper, moonshine,
WhisperLive, whisper.cpp (Whisper fallback candidates); silero-vad (needs raw
audio); claude-context (sends code to embedding/vector services by default);
Vexa (Apache-2.0 Meet bot, but its speak endpoint returned 404 in v0.12).

## 9. Testing and acceptance

**Unit (fixtures):** wake matcher (variants; mid-sentence no-trigger); stop →
muted → wake re-arm; own-seat caption lines dropped (D30); room classifier
(all-team, anonymous, dial-in, gmail, other-domain, API error → mixed); asker
matcher (duplicates, renamed outsider); "Snoop here" prefix on every spoken
answer; Chat poster refuses any non-configured space; roster loader rejects a
member outside `saasless.ai` and a duplicate email; the card text comes from the
host's roster entry; D32 stand-down picks the lower-priority host and posts once.

**Extension:** manifest grants only `https://meet.google.com/*` and the
localhost websocket (asserted by a test reading `manifest.json`); the localhost
socket rejects a connection without the token; the extension has no code path
that sends Meet chat (asserted by test).

**Sandbox:** 5.1 negative control (including the Chrome profile directory); a
prompt to write a file is refused; a registry-mcp write tool is refused and a
before/after hash shows the real `~/.agent-c` unchanged; a planted fake key is
blocked by the answer gate; Serena's exposed tool list equals the keep list
exactly, and a config with one editing tool re-enabled makes the brain refuse to
start (negative control); a planted fake key in the repo is caught before it
reaches the repo map; as `snoop`, reading the owner's GitHub token, Google
credentials or deploy key fails, and a prompt asking the brain to print its
Anthropic key yields nothing (negative controls).

**Pre-loading:** while the room is mixed, no transcript text leaves the
Conductor (assert zero brain/model calls carrying caption text); a
participant-check failure also pauses it; a planted phrase spoken in a
rehearsal is absent from every file and log on the Mac afterwards.

**End-to-end rehearsal** (test Meet; Snoop in Brett's seat on Brett's Mac;
Jeremy or Lindsay plus one more account; then repeated with Jeremy or Lindsay
as host on their own Mac):
- Acceptance questions from the 2026-10-05 standup, graded by Brett:
  - How many v1→v2 gaps are there, and how many are missing?
  - How does an accessibility-review workflow run in v2?
  - Where does multi-model support (Cursor, Gemini, OpenAI) stand?
  - What does a v2 run cost compared with Beast Mode?
- The tile shows "Snoop (<host>)"; every answer starts "Snoop here".
- Two hosts start Snoop in the same meeting: the lower-priority one stands down
  and posts once to Chat; only one Snoop answers after the first answer.
- A non-`saasless.ai` participant of each kind (gmail, other domain, anonymous,
  dial-in) joins mid-answer: speech stops; the remainder posts to Chat.
- Any participant says "peanut butter": Snoop stays silent until "Yo Snoop";
  an in-flight deep dive still posts to Chat.
- Pacing: a long answer stops after 3 sentences and asks; "yes" yields a chunk
  of roughly 75 s that ends on a complete point; a focused reply redirects the
  next chunk; silence stops speech and the full answer is in Chat.
- Snoop's own speech never triggers a wake or stop.
