# Snoop Plan 0 — Verification Spikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Revised 2026-10-06** for the Chrome-profile approach (spec D26–D32). Tasks 1, 3, 4 are unchanged in substance (Task 4's Run B now tests Brett as a non-organizer). Attendee, the `agent-c@` account and SAML (old Tasks 2, 5, 7) are gone. New: Task 5 (extension skeleton, bridge, roster), Task 6 (caption reading), Task 7 (voice + card), Task 9 (own voice + two Snoops), Task 10 (close-out).

**Goal:** Prove or disprove the spec's unverified claims (§8) before any product code is written.

**Architecture:** Each probe is small throwaway code under `spikes/` (Python) and `spikes/extension/` (a Manifest V3 Chrome extension) plus a manual procedure, producing a verdict (HOLDS / FAILS / PARTIAL) with pasted evidence in one findings file. Google admin actions and live meetings are done by the owner (Brett), with Jeremy or Lindsay for multi-person steps. A FAILS on P1 Run A, P2 caption reading, or P4 media (both extension and BlackHole) stops the program and returns to the spec.

**Tech Stack:** Python 3.12 via `uv` (`aiohttp`, `google-api-python-client`, `google-auth-oauthlib`, `claude-agent-sdk`, later `sounddevice`); Chrome (installed) with an unpacked MV3 extension; Node 24 (`node --test`, `jsdom` dev dependency for caption-parser tests); macOS `say` for probe audio; BlackHole 2ch (only if Task 7 needs the fallback).

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` (D1–D32). Read §3, §4, §5 and §8 before starting.

## Roadmap (this plan is 1 of 4)

| Plan | Scope | Written when |
|---|---|---|
| **0 (this)** | Verify §8 claims | now |
| 1 | Brain: installer, `snoop` user + negative controls, owner refresher (clone, PR/CI file, repo map, `AGENT_C_HOME` bundle), SDK sandbox config, Serena lockdown, registry-mcp, answer gate, local brain socket | after Plan 0 findings |
| 2 | Meeting seat: production extension (captions, voice, card), Conductor on Pipecat (wake/stop/mute, room + asker checks, pacing, pre-loading, D32 stand-down), Chat poster, roster-driven config | after Plan 0 findings |
| 3 | Per-host install runbook (any roster member) + end-to-end rehearsal (spec §9), Brett first | after Plans 1–2 |

Plans 1–3 target **Phase 1** (spec D33): first working Snoop on any roster member's Mac, ~1 week. Pre-loading and 75-second pacing are Phase 2.

## Global Constraints

- Internal tool for roster members only (`config/team.json`); never customer-facing (D1, §7).
- **Snoop never handles a Google password and never automates Google sign-in.** The host signs in to the "Snoop" Chrome profile themselves (D26).
- The extension is loaded **only** in the "Snoop" Chrome profile, unpacked, never published; host permission `https://meet.google.com/*` only (D27).
- The extension never sends Meet chat, email, or any keystroke/click into Meet except turning captions on (D17).
- No secret is ever printed through a tool, committed, or pasted into findings. Compare secrets by sha256 prefix only. Key files live in `spikes/.secrets/` (gitignored) and are deleted at the end of Plan 0.
- **No meeting text or real names are committed.** Caption DOM captures go to `/tmp` and are deleted the same day; any committed fixture is rewritten with test names and test sentences (Task 6 Step 3 checks this).
- Every gate probe has a **negative control** (must fail) and a **positive control** (must succeed), both recorded.
- Times in findings are Pacific (PDT), labeled.
- Disk: 31.9 GiB free on 2026-10-06. Stop if under 25 GiB.
- Python 3.12 (not the system 3.14) — pinned in `pyproject.toml`.

## Review Focus

1. **Any local process drives Snoop's voice** — the localhost bridge must reject a connection without the token, or anything on the Mac could speak in a meeting as Brett. Pinned in Task 5, Step 2.
2. **Meet ignores the injected mic and uses the real one** — Snoop would be silent and the room would hear Brett's laptop mic. Expected: others hear `say` audio, not room noise. Pinned in Task 7, Step 4.
3. **Snoop reacts to its own voice** — its own speech must never trigger wake or stop. Pinned in Task 9, Steps 1–4.
4. **Real meeting text lands in the repo** — the caption fixture must contain only test strings. Pinned in Task 6, Step 3.
5. **A non-organizer host cannot read participants** — then Snoop hosted by anyone but the organizer is Chat-only. Expected: recorded, not assumed. Pinned in Task 4, Step 6.

---

### Task 1: Spike scaffold and secret hygiene

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `spikes/__init__.py`
- Create: `spikes/common.py`
- Create: `docs/superpowers/findings/2026-10-plan-0-findings.md`
- Test: `spikes/test_common.py`

**Interfaces:**
- Produces: `spikes.common.pdt_now() -> str` (ISO time, PDT label); `spikes.common.sha_prefix(value: str) -> str` (first 12 hex of sha256); `spikes.common.SECRETS_DIR: pathlib.Path` (`spikes/.secrets`, created with mode 700).

- [ ] **Step 1: Write `.gitignore` before anything else exists**

```gitignore
spikes/.secrets/
*.pem
*.p12
*-key.json
client_secret*.json
token*.json
.env
.env.*
__pycache__/
.venv/
*.wav
```

- [ ] **Step 2: Write the failing test**

```python
# spikes/test_common.py
import stat
from spikes.common import pdt_now, sha_prefix, SECRETS_DIR

def test_sha_prefix_is_12_hex_and_stable():
    assert sha_prefix("abc") == "ba7816bf8f01"
    assert len(sha_prefix("anything")) == 12

def test_pdt_now_is_labeled():
    assert pdt_now().endswith((" PDT", " PST"))

def test_secrets_dir_is_private_and_ignored():
    assert SECRETS_DIR.exists()
    assert stat.S_IMODE(SECRETS_DIR.stat().st_mode) == 0o700
```

- [ ] **Step 3: Write `pyproject.toml` and run the test to verify it fails**

```toml
[project]
name = "yo-snoop-spikes"
version = "0.0.0"
requires-python = "==3.12.*"
dependencies = [
  "google-api-python-client>=2.150",
  "google-auth-oauthlib>=1.2",
  "google-cloud-texttospeech>=2.20",
  "aiohttp>=3.10",
  "websockets>=13",
  "claude-agent-sdk",
]

[dependency-groups]
dev = ["pytest>=8"]
```

Run: `cd ~/Code/Saasless/yo-snoop && uv sync && uv run pytest spikes/test_common.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spikes.common'`

- [ ] **Step 4: Write minimal implementation**

```python
# spikes/common.py
import hashlib
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
SECRETS_DIR = pathlib.Path(__file__).parent / ".secrets"
SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
SECRETS_DIR.chmod(0o700)


def pdt_now() -> str:
    now = datetime.now(PACIFIC)
    return now.strftime("%Y-%m-%d %H:%M:%S ") + now.tzname()


def sha_prefix(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]
```

Create empty `spikes/__init__.py`.

- [ ] **Step 5: Run tests to verify they pass, and prove the ignore works**

Run: `uv run pytest spikes/test_common.py -v`
Expected: 3 PASS

Run: `touch spikes/.secrets/probe && git check-ignore -v spikes/.secrets/probe; rc=$?; echo "rc=$rc"; rm spikes/.secrets/probe`
Expected: a line naming `.gitignore` and `rc=0`. If `rc=1`, stop — the ignore rule is broken.

- [ ] **Step 6: Create the findings file**

```markdown
# Plan 0 findings

Spec: docs/superpowers/specs/2026-10-05-yo-snoop-design.md · Plan: docs/superpowers/plans/2026-10-05-plan-0-verification-spikes.md

| Probe | Spec ref | Verdict | Evidence below | Consequence for Plans 1–2 |
|---|---|---|---|---|
| P1 Meet participants principal + latency | §8.1, §4 step 4 | | | |
| P2 Caption latency + wake accuracy | §8.2, §4 step 3 | | | |
| P3 Claude Code headless controls | §8.3, §5.3 | | | |
| P4 Attendee SAML, OU-scoped | §8.4, §3.3 | | | |
| P5 Chat app, one space, three users | §8.5, §3.1 | | | |
| P6 Audio stop latency (unlisted risk) | §4 step 2 | | | |

Verdicts: HOLDS / FAILS / PARTIAL. Every verdict cites pasted command output. No secrets.
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml uv.lock spikes/__init__.py spikes/common.py spikes/test_common.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: scaffold, secret hygiene, findings template"
```

---

### Task 2: Owner setup — Cloud project, Google Group, Snoop Chrome profile (manual, Brett)

No new Google account and no new seat (D26). Admin console and Cloud console are clicked by Brett; the executor guides.

**Files:**
- Modify: `docs/superpowers/findings/2026-10-plan-0-findings.md` (append "Setup log")

**Interfaces:**
- Produces: Google Cloud project `yo-snoop` with Meet REST API, Google Chat API, People API, Cloud Text-to-Speech API enabled; OAuth consent **Internal**; a **Desktop** OAuth client at `spikes/.secrets/client_secret.json`; Google Group `snoop-team@startup.ai` with brett@, jeremy@, lindsay@; Chrome profile **"Snoop"** signed in as brett@ by Brett.

- [ ] **Step 1: Cloud project** — console.cloud.google.com → new project `yo-snoop` under the saasless.ai organization. Enable: Google Meet REST API, Google Chat API, People API, Cloud Text-to-Speech API. OAuth consent screen: **Internal**. Credentials → OAuth client ID → Desktop app → download JSON to `~/Code/Saasless/yo-snoop/spikes/.secrets/client_secret.json`.
- [ ] **Step 2: Google Group** — Admin console → Directory → Groups → create `snoop-team@startup.ai`, members brett@, jeremy@, lindsay@. Access: members only; no external members.
- [ ] **Step 3: Snoop Chrome profile** — Chrome → profile menu → Add → "Snoop" → sign in as brett@ (Brett types his own password; nothing records it). Turn off Chrome sync for this profile's passwords and autofill. This profile is used only for Snoop meetings.
- [ ] **Step 4: Verify without printing secrets**

Run: `ls -l ~/Code/Saasless/yo-snoop/spikes/.secrets/ && git -C ~/Code/Saasless/yo-snoop status --porcelain spikes/.secrets`
Expected: `client_secret.json` listed; `git status` prints nothing (ignored).

- [ ] **Step 5: Record and commit** — append to findings under `## Setup log`: date/time (PDT), each item done, by whom.

```bash
git add docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "findings: owner setup log"
```

---

### Task 3: Probe P3 — Claude Code headless controls (§8.3)

Runs first among probes: it needs no Google setup.

**Files:**
- Create: `spikes/p3_flags.sh`
- Create: `spikes/p3_sandbox_probe.py`
- Create: `spikes/p3_session_probe.py`
- Modify: findings (P3 row + evidence)

**Interfaces:**
- Consumes: `spikes.common.pdt_now`
- Produces (findings, consumed by Plan 1): the exact flag/setting names that exist for allow-list, deny-list, unlisted-tool behavior, MCP config, persistent session, and API key helper.

- [ ] **Step 1: Probe the real signature before using it**

```bash
# spikes/p3_flags.sh
set -u
claude --version
claude --help > /tmp/claude-help.txt 2>&1
for f in --allowedTools --allowed-tools --disallowedTools --disallowed-tools \
         --permission-mode --settings --mcp-config --strict-mcp-config \
         --input-format --output-format --resume --continue --max-turns \
         --append-system-prompt --setting-sources; do
  if grep -q -- "$f" /tmp/claude-help.txt; then echo "PRESENT $f"; else echo "ABSENT  $f"; fi
done
grep -A3 -- "--permission-mode" /tmp/claude-help.txt
uv run python - <<'PY'
import inspect, claude_agent_sdk as s
print("sdk", getattr(s, "__version__", "?"))
print(inspect.signature(s.ClaudeAgentOptions))
print("ClaudeSDKClient" , hasattr(s, "ClaudeSDKClient"))
PY
```

Run: `bash spikes/p3_flags.sh | tee /tmp/p3-flags.txt`
Expected: a PRESENT/ABSENT line per flag, the permission-mode choices, and the SDK options signature. Paste into findings verbatim. **Use only names marked PRESENT in Steps 2–6; if a name below is ABSENT, substitute the PRESENT equivalent and note it.**

- [ ] **Step 2: Write the sandbox probe (positive + negative controls)**

```python
# spikes/p3_sandbox_probe.py
"""Negative/positive controls for Claude Code headless tool restrictions.
Runs claude -p in a temp dir with a Read/Grep/Glob/git-log-only settings file."""
import json, subprocess, sys, tempfile, pathlib
from spikes.common import pdt_now

SETTINGS = {
    "permissions": {
        "allow": ["Read", "Grep", "Glob", "Bash(git log:*)"],
        "deny": ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task"],
    }
}

def run(prompt: str, cwd: pathlib.Path, settings_path: pathlib.Path) -> list[dict]:
    cmd = ["claude", "-p", prompt, "--settings", str(settings_path),
           "--output-format", "stream-json", "--verbose", "--max-turns", "4"]
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
    events = []
    for line in out.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events

def text_of(events: list[dict]) -> str:
    return json.dumps(events)

def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "canary.txt").write_text("CANARY-7f3a")
        settings = root / "settings.json"
        settings.write_text(json.dumps(SETTINGS))
        results = {}

        ev = run("Read canary.txt and reply with its exact contents only.", root, settings)
        results["positive_read"] = "CANARY-7f3a" in text_of(ev)

        run("Create a file named pwned.txt containing the word hi. Do it now.", root, settings)
        results["negative_write_blocked"] = not (root / "pwned.txt").exists()

        ev = run("Run this shell command and show the output: curl -s https://example.com", root, settings)
        results["negative_network_blocked"] = "Example Domain" not in text_of(ev)

        ev = run("Run: touch shell-made.txt", root, settings)
        results["negative_shell_blocked"] = not (root / "shell-made.txt").exists()

    print(pdt_now(), json.dumps(results, indent=2))
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run it**

Run: `uv run python -m spikes.p3_sandbox_probe; rc=$?; echo "rc=$rc"`
Expected: all four keys `true`, `rc=0`. **If `positive_read` is false, the harness is broken — the negative results mean nothing.** Fix the harness before recording a verdict.

- [ ] **Step 4: Prove the negative control can fail**

Temporarily change `SETTINGS["permissions"]["allow"]` to add `"Write"` and remove it from `deny`, rerun.
Expected: `negative_write_blocked: false`, `rc=1`. Revert the change. Record both runs in findings.

- [ ] **Step 5: Persistent session + cache probe**

```python
# spikes/p3_session_probe.py
"""One session, two questions: does context carry over, and does the cache hit?"""
import asyncio, json, time
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage
from spikes.common import pdt_now

async def ask(client, prompt):
    t0 = time.monotonic()
    await client.query(prompt)
    text, usage = "", None
    async for msg in client.receive_response():
        if isinstance(msg, ResultMessage):
            usage = msg.usage
            text = msg.result or ""
    return text, usage, round(time.monotonic() - t0, 2)

async def main():
    opts = ClaudeAgentOptions(allowed_tools=[], max_turns=1,
                              system_prompt="Answer in one short sentence.")
    async with ClaudeSDKClient(options=opts) as client:
        a1 = await ask(client, "Remember the number 4182. Reply 'ok'.")
        a2 = await ask(client, "What number did I ask you to remember?")
    print(pdt_now(), json.dumps({"q1": a1, "q2": a2}, default=str, indent=2))
    assert "4182" in a2[0], "context did not carry over"

asyncio.run(main())
```

Run: `uv run python -m spikes.p3_session_probe; rc=$?; echo "rc=$rc"`
Expected: `rc=0`; q2's text contains `4182`; q2 `usage` shows `cache_read_input_tokens` > 0. Record both latencies. If the Step 1 signature differs from these names, adapt to the PRESENT names and note it.

- [ ] **Step 6: API key helper probe — DEFERRED to Plan 1 (D25, 2026-10-05).** Development runs on the owner's subscription; the key helper only matters for the production API key. Kept below for Plan 1 to reuse.

  *(Original step text:)* **API key helper probe (Brett stores the key; never printed)**

Brett creates a Console workspace `Snoop` with a monthly spend limit and an API key in it, then stores it through `security`'s interactive shell, so the key never appears in a process list or shell history (a command line containing a key *is* the key; and the plain `-w` prompt truncates long keys at 128 characters):

```bash
security -i
```

At the `security>` prompt type `add-generic-password -U -s snoop-anthropic -a snoop -w ` then paste the key, press Enter, then type `quit`.

Then verify length and the helper without printing the key:

```bash
security find-generic-password -s snoop-anthropic -a snoop -w | tr -d '\n' | wc -c
```

Expected: the full key length (not 128). Then run a one-question probe with a settings file containing `"apiKeyHelper": "security find-generic-password -s snoop-anthropic -a snoop -w"` (only if `apiKeyHelper` is a supported settings key per Step 1/docs) and `ANTHROPIC_API_KEY` unset; expected: an answer, and the Console's Snoop workspace shows the usage. Clear clipboard afterwards: `pbcopy < /dev/null`.

- [ ] **Step 7: Record verdict and commit**

```bash
git add spikes/p3_flags.sh spikes/p3_sandbox_probe.py spikes/p3_session_probe.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P3 Claude Code headless controls"
```

---

### Task 4: Probe P1 — Meet participants: principal and latency (§8.1)

**Files:**
- Create: `spikes/p1_meet_participants.py`
- Test: `spikes/test_p1_classify.py`
- Modify: findings (P1 row + evidence)

**Interfaces:**
- Consumes: Task 2 OAuth client; `spikes.common.SECRETS_DIR`, `pdt_now`
- Produces: `classify(participant: dict) -> tuple[str, str | None, str]` returning `(kind, user_id, display_name)` where kind ∈ `{"signed_in","anonymous","phone"}`. Plan 2's room check will reuse this shape.

- [ ] **Step 1: Write the failing test**

```python
# spikes/test_p1_classify.py
from spikes.p1_meet_participants import classify

def test_signed_in():
    p = {"signedinUser": {"user": "users/123", "displayName": "Brett Evans"}}
    assert classify(p) == ("signed_in", "users/123", "Brett Evans")

def test_anonymous():
    assert classify({"anonymousUser": {"displayName": "Brett Evans"}}) == ("anonymous", None, "Brett Evans")

def test_phone():
    assert classify({"phoneUser": {"displayName": "+1 415"}}) == ("phone", None, "+1 415")

def test_unknown_shape_is_treated_as_anonymous():
    assert classify({}) == ("anonymous", None, "")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest spikes/test_p1_classify.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the probe**

```python
# spikes/p1_meet_participants.py
"""Poll Meet REST participants for a live meeting; print each change with PDT time.
Usage: uv run python -m spikes.p1_meet_participants --code abc-defg-hij --as brett"""
import argparse, time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from spikes.common import SECRETS_DIR, pdt_now

SCOPES = ["https://www.googleapis.com/auth/meetings.space.readonly",
          "https://www.googleapis.com/auth/directory.readonly"]

def classify(p: dict) -> tuple[str, str | None, str]:
    if "signedinUser" in p:
        u = p["signedinUser"]
        return "signed_in", u.get("user"), u.get("displayName", "")
    if "phoneUser" in p:
        return "phone", None, p["phoneUser"].get("displayName", "")
    a = p.get("anonymousUser", {})
    return "anonymous", None, a.get("displayName", "")

def creds_for(who: str) -> Credentials:
    tok = SECRETS_DIR / f"token-{who}.json"
    if tok.exists():
        c = Credentials.from_authorized_user_file(str(tok), SCOPES)
        if c.valid:
            return c
        if c.expired and c.refresh_token:
            c.refresh(Request())
            tok.write_text(c.to_json()); tok.chmod(0o600)
            return c
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_DIR / "client_secret.json"), SCOPES)
    c = flow.run_local_server(port=0)
    tok.write_text(c.to_json()); tok.chmod(0o600)
    return c

def email_for(people, user_id: str) -> str | None:
    pid = user_id.split("/", 1)[1]
    try:
        r = people.people().get(resourceName=f"people/{pid}", personFields="emailAddresses").execute()
        emails = r.get("emailAddresses", [])
        return emails[0]["value"] if emails else None
    except Exception as e:  # recorded, not hidden
        return f"LOOKUP-ERROR {type(e).__name__}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--as", dest="who", required=True)
    ap.add_argument("--seconds", type=int, default=300)
    a = ap.parse_args()
    c = creds_for(a.who)
    meet = build("meet", "v2", credentials=c)
    people = build("people", "v1", credentials=c)
    seen: dict[str, str] = {}
    end = time.monotonic() + a.seconds
    while time.monotonic() < end:
        t0 = time.monotonic()
        try:
            recs = meet.conferenceRecords().list(
                filter=f'space.meeting_code = "{a.code}" AND end_time IS NULL').execute()
        except Exception as e:
            print(pdt_now(), "LIST-ERROR", type(e).__name__, str(e)[:200]); time.sleep(1); continue
        for rec in recs.get("conferenceRecords", []):
            ps = meet.conferenceRecords().participants().list(parent=rec["name"]).execute()
            for p in ps.get("participants", []):
                kind, uid, name = classify(p)
                state = "left" if p.get("latestEndTime") else "present"
                key = p["name"]
                if seen.get(key) != state:
                    seen[key] = state
                    email = email_for(people, uid) if uid else None
                    print(pdt_now(), f"{state:7} {kind:9} {name!r} {email} api_ms={int((time.monotonic()-t0)*1000)}")
        time.sleep(max(0, 1 - (time.monotonic() - t0)))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the unit test**

Run: `uv run pytest spikes/test_p1_classify.py -v`
Expected: 4 PASS

- [ ] **Step 5: Live run A — Brett is the organizer**

Brett creates a Meet from his brett@ calendar. Start: `uv run python -m spikes.p1_meet_participants --code <code> --as brett`. Sign in via the browser that opens as brett@ (read-only Meet + directory scopes only). Then, noting the clock (PDT) at each click:
1. Join from a **private window, not signed in** (anonymous). 2. Join from jeremy@ or lindsay@. 3. Dial in by phone if available. 4. Leave each.

Expected per event: a line with the right `kind`; for saasless users an `@startup.ai` email; time from click to line recorded. **Compute p50/p90 join-to-appearance across ≥ 5 joins.** Pass bar for HOLDS: anonymous joiner appears within 10 s p90.

- [ ] **Step 6: Live run B — Brett is a participant, not the organizer**

Jeremy or Lindsay creates a Meet from their own calendar and invites brett@. Brett joins it (in the Snoop Chrome profile from Task 2), then runs `uv run python -m spikes.p1_meet_participants --code <code> --as brett` with the same token.
Expected (record whichever happens): participants listed → **any host's own read-only token works for any meeting they attend** (D13/D24 satisfied); `LIST-ERROR`/empty → only the organizer's token can read the list, so Snoop hosted by a non-organizer would treat every such meeting as mixed (Chat-only) — record it; it changes Plan 2's room check (host must be organizer, or organizer shares a read-only token). If Jeremy or Lindsay can, repeat Run A with them as organizer running the probe on their own token.

- [ ] **Step 7: Verdict and commit** — P1 HOLDS if the host's own read-only token sees live participants with kind + resolvable saasless identity within the bar in Run A, and Run B's result is recorded. FAILS → stop; return to spec owner.

```bash
git add spikes/p1_meet_participants.py spikes/test_p1_classify.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P1 Meet participants principal and latency"
```

---

### Task 5: Extension skeleton, localhost bridge, roster (code only — no meeting needed)

**Files:**
- Create: `spikes/roster.py`, `spikes/test_roster.py`
- Create: `spikes/bridge_server.py`, `spikes/test_bridge_server.py`
- Create: `spikes/make_ext_config.py`
- Create: `spikes/extension/manifest.json`, `spikes/extension/bridge_sw.js`, `spikes/extension/content.js`, `spikes/extension/page_media.js`
- Create: `spikes/test_extension_manifest.py`
- Modify: `.gitignore` (add `spikes/extension/config.local.json`)

**Interfaces:**
- Consumes: `config/team.json` (D31); `spikes.common.SECRETS_DIR`, `pdt_now`
- Produces:
  - `spikes.roster.load(path: str | Path) -> Roster`; `Roster.members: tuple[Member, ...]`; `Roster.by_email(email) -> Member | None`; `Roster.by_display_name(name) -> list[Member]`; `Member(email, display_name, host_priority, may_host, mixed_room_asker)`. Raises `ValueError` on bad roster.
  - `spikes.bridge_server.make_app(token: str, on_message: Callable[[dict], None]) -> aiohttp.web.Application` serving websocket `/snoop`; first client message must be `{"type": "hello", "token": <token>}` within 5 s, else close code **4401**; on success the server sends `{"type": "ack"}`. `app["clients"]: set` of live sockets for sending `{"type": "audio"|"stop"|"card"|"dump"}` messages.
  - Extension message protocol: page → server `{"type": "caption", "speaker": str, "text": str, "ts": float}` and `{"type": "dump", "html": str}`; server → page `{"type": "audio", "pcm_b64": str, "rate": int}`, `{"type": "stop"}`, `{"type": "card", "text": str}`, `{"type": "dump"}`.

- [ ] **Step 1: Roster — failing tests**

```python
# spikes/test_roster.py
import json, pytest
from spikes.roster import load

def write(tmp_path, members, domain="startup.ai"):
    p = tmp_path / "team.json"
    p.write_text(json.dumps({"domain": domain, "google_group": "snoop-team@startup.ai", "members": members}))
    return p

def m(email, name, prio):
    return {"email": email, "display_name": name, "host_priority": prio, "may_host": True, "mixed_room_asker": True}

def test_repo_roster_loads():
    r = load("config/team.json")
    assert [x.email for x in r.members] == ["brett@startup.ai", "jeremy@startup.ai", "lindsay@startup.ai"]
    assert r.by_email("jeremy@startup.ai").display_name == "Jeremy Leeds"

def test_rejects_outside_domain(tmp_path):
    with pytest.raises(ValueError, match="domain"):
        load(write(tmp_path, [m("x@gmail.com", "X", 1)]))

def test_rejects_duplicate_email(tmp_path):
    with pytest.raises(ValueError, match="duplicate email"):
        load(write(tmp_path, [m("a@startup.ai", "A", 1), m("a@startup.ai", "B", 2)]))

def test_rejects_duplicate_priority(tmp_path):
    with pytest.raises(ValueError, match="duplicate host_priority"):
        load(write(tmp_path, [m("a@startup.ai", "A", 1), m("b@startup.ai", "B", 1)]))

def test_rejects_duplicate_display_name(tmp_path):
    with pytest.raises(ValueError, match="duplicate display_name"):
        load(write(tmp_path, [m("a@startup.ai", "Sam", 1), m("b@startup.ai", "Sam", 2)]))
```

Run: `uv run pytest spikes/test_roster.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spikes.roster'`

- [ ] **Step 2: Roster — implement, then green**

```python
# spikes/roster.py
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Member:
    email: str
    display_name: str
    host_priority: int
    may_host: bool
    mixed_room_asker: bool


@dataclass(frozen=True)
class Roster:
    domain: str
    google_group: str
    members: tuple[Member, ...]

    def by_email(self, email: str) -> Member | None:
        return next((x for x in self.members if x.email == email.lower()), None)

    def by_display_name(self, name: str) -> list[Member]:
        return [x for x in self.members if x.display_name == name]


def _dupes(values):
    seen, dup = set(), set()
    for v in values:
        (dup if v in seen else seen).add(v)
    return dup


def load(path) -> Roster:
    raw = json.loads(Path(path).read_text())
    domain = raw["domain"].lower()
    members = tuple(Member(email=x["email"].lower(), display_name=x["display_name"],
                           host_priority=int(x["host_priority"]), may_host=bool(x["may_host"]),
                           mixed_room_asker=bool(x["mixed_room_asker"])) for x in raw["members"])
    for x in members:
        if not x.email.endswith("@" + domain):
            raise ValueError(f"member outside domain {domain}: {x.email}")
    for field, label in (("email", "email"), ("host_priority", "host_priority"), ("display_name", "display_name")):
        d = _dupes(getattr(x, field) for x in members)
        if d:
            raise ValueError(f"duplicate {label}: {sorted(map(str, d))}")
    return Roster(domain=domain, google_group=raw["google_group"], members=members)
```

Run: `uv run pytest spikes/test_roster.py -v`
Expected: 5 PASS

- [ ] **Step 3: Bridge server — failing tests (token is the gate)**

```python
# spikes/test_bridge_server.py
import asyncio
from aiohttp import WSMsgType
from aiohttp.test_utils import TestServer, TestClient
from spikes.bridge_server import make_app

TOKEN = "t-123"

async def _client(app):
    c = TestClient(TestServer(app)); await c.start_server(); return c

def test_rejects_connection_without_hello():
    async def go():
        c = await _client(make_app(TOKEN, lambda m: None, hello_timeout=0.2))
        ws = await c.ws_connect("/snoop")
        msg = await ws.receive()
        await c.close()
        return msg, ws.close_code
    msg, code = asyncio.run(go())
    assert msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING) and code == 4401

def test_rejects_wrong_token():
    async def go():
        c = await _client(make_app(TOKEN, lambda m: None))
        ws = await c.ws_connect("/snoop")
        await ws.send_json({"type": "hello", "token": "wrong"})
        await ws.receive()
        code = ws.close_code
        await c.close()
        return code
    assert asyncio.run(go()) == 4401

def test_accepts_right_token_and_forwards_messages():
    got = []
    async def go():
        c = await _client(make_app(TOKEN, got.append))
        ws = await c.ws_connect("/snoop")
        await ws.send_json({"type": "hello", "token": TOKEN})
        ack = await ws.receive_json()
        await ws.send_json({"type": "caption", "speaker": "Test A", "text": "hello", "ts": 1.0})
        await asyncio.sleep(0.05)
        await ws.close(); await c.close()
        return ack
    assert asyncio.run(go()) == {"type": "ack"}
    assert got == [{"type": "caption", "speaker": "Test A", "text": "hello", "ts": 1.0}]
```

Run: `uv run pytest spikes/test_bridge_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spikes.bridge_server'`

- [ ] **Step 4: Bridge server — implement, then green**

```python
# spikes/bridge_server.py
"""Localhost websocket between the Snoop extension and Snoop's Python side.
Binds 127.0.0.1 only. First message must be a hello carrying the per-install token."""
import asyncio, hmac
from typing import Callable
from aiohttp import web, WSMsgType


def make_app(token: str, on_message: Callable[[dict], None], hello_timeout: float = 5.0) -> web.Application:
    app = web.Application()
    app["clients"] = set()

    async def snoop(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        try:
            first = await asyncio.wait_for(ws.receive_json(), timeout=hello_timeout)
        except Exception:
            await ws.close(code=4401, message=b"hello required"); return ws
        if first.get("type") != "hello" or not hmac.compare_digest(str(first.get("token", "")), token):
            await ws.close(code=4401, message=b"bad token"); return ws
        await ws.send_json({"type": "ack"})
        app["clients"].add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    on_message(msg.json())
        finally:
            app["clients"].discard(ws)
        return ws

    app.router.add_get("/snoop", snoop)
    return app


async def broadcast(app: web.Application, message: dict) -> None:
    for ws in list(app["clients"]):
        await ws.send_json(message)
```

Run: `uv run pytest spikes/test_bridge_server.py -v`
Expected: 3 PASS

- [ ] **Step 5: Extension manifest — failing test (least privilege)**

```python
# spikes/test_extension_manifest.py
import json, pathlib, re

EXT = pathlib.Path("spikes/extension")

def manifest():
    return json.loads((EXT / "manifest.json").read_text())

def test_only_meet_host_permission():
    m = manifest()
    assert m["manifest_version"] == 3
    assert m["host_permissions"] == ["https://meet.google.com/*"]
    assert m.get("permissions", []) == []
    assert "externally_connectable" not in m and "optional_permissions" not in m
    for cs in m["content_scripts"]:
        assert cs["matches"] == ["https://meet.google.com/*"]

def test_no_input_or_chat_code_paths():
    banned = [r"\.value\s*=", r"dispatchEvent\(", r"KeyboardEvent", r"InputEvent", r"chat", r"sendKeys"]
    for js in EXT.glob("*.js"):
        src = js.read_text()
        for pat in banned:
            assert not re.search(pat, src, re.IGNORECASE), f"{js.name} matches {pat}"
        clicks = re.findall(r"\.click\(\)", src)
        assert len(clicks) <= 1 and (not clicks or "function turnOnCaptions" in src), f"{js.name} clicks outside turnOnCaptions"

def test_local_config_is_ignored():
    import subprocess
    p = EXT / "config.local.json"
    p.write_text("{}")
    try:
        assert subprocess.run(["git", "check-ignore", "-q", str(p)]).returncode == 0
    finally:
        p.unlink()
```

Run: `uv run pytest spikes/test_extension_manifest.py -v`
Expected: FAIL (`FileNotFoundError` for `manifest.json`)

- [ ] **Step 6: Extension files — write, then green**

`.gitignore` gains the line `spikes/extension/config.local.json`.

```json
// spikes/extension/manifest.json
{
  "manifest_version": 3,
  "name": "Snoop (spike)",
  "version": "0.0.1",
  "description": "Internal Saasless spike. Meet captions out; Snoop voice and card in.",
  "host_permissions": ["https://meet.google.com/*"],
  "background": {"service_worker": "bridge_sw.js"},
  "content_scripts": [
    {"matches": ["https://meet.google.com/*"], "js": ["page_media.js"], "world": "MAIN", "run_at": "document_start"},
    {"matches": ["https://meet.google.com/*"], "js": ["content.js"], "run_at": "document_idle"}
  ]
}
```

(The `//` line above is a label in this plan, not part of the file — the file must be valid JSON.)

```js
// spikes/extension/bridge_sw.js — holds the localhost websocket; relays to/from the Meet tab.
let ws = null, port = null, cfg = null;

async function config() {
  if (!cfg) cfg = await (await fetch(chrome.runtime.getURL("config.local.json"))).json();
  return cfg;
}

async function connect() {
  const c = await config();
  ws = new WebSocket(`ws://127.0.0.1:${c.port}/snoop`);
  ws.onopen = () => ws.send(JSON.stringify({type: "hello", token: c.token}));
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.type !== "ack" && port) port.postMessage(m); };
  ws.onclose = () => { ws = null; setTimeout(connect, 2000); };
}

chrome.runtime.onConnect.addListener((p) => {
  if (p.name !== "snoop-meet") return;
  port = p;
  config().then((c) => p.postMessage({type: "card", text: `Snoop (${c.host_display_name})`}));
  p.onMessage.addListener((m) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); });
  p.onDisconnect.addListener(() => { port = null; });
  if (!ws) connect();
});
```

```js
// spikes/extension/content.js — isolated world: relays between the service worker and page_media.js;
// reads captions (selectors filled in by Task 6).
const port = chrome.runtime.connect({name: "snoop-meet"});
const TAG = "snoop-spike";

port.onMessage.addListener((m) => {
  if (m.type === "dump") { port.postMessage({type: "dump", html: captionRegionHTML()}); return; }
  window.postMessage({tag: TAG, dir: "to-page", msg: m}, location.origin);
});

function captionRegionHTML() {
  const el = document.querySelector('[role="region"][aria-label*="aption" i]') || document.querySelector("[aria-live]");
  return el ? el.outerHTML : "NO-CAPTION-REGION";
}

// Task 6 replaces this with a parser built from a captured fixture.
function emitCaption(speaker, text) {
  port.postMessage({type: "caption", speaker, text, ts: Date.now() / 1000});
}
```

```js
// spikes/extension/page_media.js — MAIN world, document_start: supplies Snoop's mic and camera to Meet.
(() => {
  const TAG = "snoop-spike";
  const ac = new AudioContext({sampleRate: 24000});
  const dest = ac.createMediaStreamDestination();
  let sources = [], playHead = 0, cardText = "Snoop";

  const canvas = document.createElement("canvas");
  canvas.width = 1280; canvas.height = 720;
  const g = canvas.getContext("2d");
  function drawCard() {
    g.fillStyle = "#111"; g.fillRect(0, 0, 1280, 720);
    g.fillStyle = "#fff"; g.font = "bold 72px sans-serif"; g.textAlign = "center";
    g.fillText(cardText, 640, 380);
  }
  drawCard(); setInterval(drawCard, 1000);
  const cardTrack = canvas.captureStream(5).getVideoTracks()[0];

  function playPcm(b64, rate) {
    const bytes = Uint8Array.from(atob(b64), (ch) => ch.charCodeAt(0));
    const samples = new Int16Array(bytes.buffer);
    const buf = ac.createBuffer(1, samples.length, rate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < samples.length; i++) ch[i] = samples[i] / 32768;
    const src = ac.createBufferSource();
    src.buffer = buf; src.connect(dest);
    playHead = Math.max(playHead, ac.currentTime);
    src.start(playHead); playHead += buf.duration;
    sources.push(src); src.onended = () => { sources = sources.filter((s) => s !== src); };
  }
  function stopAll() { sources.forEach((s) => { try { s.stop(); } catch (e) {} }); sources = []; playHead = ac.currentTime; }

  window.addEventListener("message", (e) => {
    if (e.source !== window || e.data?.tag !== TAG || e.data.dir !== "to-page") return;
    const m = e.data.msg;
    if (m.type === "audio") { ac.resume(); playPcm(m.pcm_b64, m.rate); }
    else if (m.type === "stop") stopAll();
    else if (m.type === "card") cardText = m.text;
  });

  const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = async (constraints = {}) => {
    const tracks = [];
    if (constraints.audio) tracks.push(dest.stream.getAudioTracks()[0].clone());
    if (constraints.video) tracks.push(cardTrack.clone());
    if (!tracks.length) return real(constraints);
    return new MediaStream(tracks);
  };
})();
```

```python
# spikes/make_ext_config.py
"""Write spikes/extension/config.local.json (gitignored) with a fresh token and the host's card name.
Usage: uv run python -m spikes.make_ext_config --host brett@startup.ai [--port 8790]"""
import argparse, json, secrets
from pathlib import Path
from spikes.common import SECRETS_DIR, sha_prefix
from spikes.roster import load

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--host", required=True); ap.add_argument("--port", type=int, default=8790)
    a = ap.parse_args()
    member = load("config/team.json").by_email(a.host)
    if member is None or not member.may_host:
        raise SystemExit(f"{a.host} is not a roster member who may host")
    token = secrets.token_urlsafe(32)
    (SECRETS_DIR / "bridge-token").write_text(token); (SECRETS_DIR / "bridge-token").chmod(0o600)
    p = Path("spikes/extension/config.local.json")
    p.write_text(json.dumps({"port": a.port, "token": token, "host_display_name": member.display_name}))
    p.chmod(0o600)
    print("wrote config; token sha", sha_prefix(token), "card", f"Snoop ({member.display_name})")

if __name__ == "__main__":
    main()
```

Run: `uv run pytest spikes/test_extension_manifest.py -v`
Expected: 3 PASS

- [ ] **Step 7: Load the extension (Brett, no meeting needed)** — in the "Snoop" profile: `chrome://extensions` → Developer mode → Load unpacked → `~/Code/Saasless/yo-snoop/spikes/extension`. Run `uv run python -m spikes.make_ext_config --host brett@startup.ai` first. Expected: extension loads with no errors; its details page lists site access "meet.google.com" only.

- [ ] **Step 8: Full suite and commit**

Run: `uv run pytest -q`
Expected: all pass (Task 1, 3–5 tests).

```bash
git add .gitignore spikes/roster.py spikes/test_roster.py spikes/bridge_server.py spikes/test_bridge_server.py spikes/make_ext_config.py spikes/extension/manifest.json spikes/extension/bridge_sw.js spikes/extension/content.js spikes/extension/page_media.js spikes/test_extension_manifest.py
git commit -m "spikes: extension skeleton, token-gated localhost bridge, roster loader"
```

---

### Task 6: Probe P2 — reading Meet captions in the extension (§8.2)

**Files:**
- Create: `spikes/p2_capture.py` (server that requests a caption-region dump and writes it to `/tmp`)
- Create: `spikes/extension/caption_parse.js`, `spikes/extension/test/caption_parse.test.mjs`, `spikes/extension/test/fixture_captions.html`, `spikes/extension/package.json`
- Create: `spikes/test_fixture_is_sanitized.py`
- Create: `spikes/p2_listen.py` (logs caption events with receipt time)
- Modify: `spikes/extension/content.js`, `spikes/extension/manifest.json` (add `caption_parse.js` before `content.js`)
- Delete: `spikes/p2_receiver.py` (Attendee webhook receiver — obsolete)
- Reuse: `spikes/p2_wake.py`, `spikes/test_p2_wake.py`, `spikes/p2_mark.py`, `spikes/p2_script.txt`

**Interfaces:**
- Consumes: Task 5 bridge + extension
- Produces: `parseCaptions(root: Element) -> Array<{speaker: string, text: string}>` (global in the content script; exported for Node tests via `module.exports` guard)

- [ ] **Step 1: Capture the caption DOM (Brett, live, alone in a test meeting)**

```python
# spikes/p2_capture.py
"""Ask the extension for the caption region's HTML and save it to /tmp (never the repo)."""
import asyncio, json, time
from aiohttp import web
from spikes.bridge_server import make_app, broadcast
from spikes.common import SECRETS_DIR, pdt_now

def on_message(m):
    if m.get("type") == "dump":
        path = f"/tmp/snoop-caption-dom-{int(time.time())}.html"
        open(path, "w").write(m["html"])
        print(pdt_now(), "saved", path, len(m["html"]), "chars")

async def main():
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    print("speak a few lines with captions on, then press Enter to dump")
    while True:
        await asyncio.get_running_loop().run_in_executor(None, input)
        await broadcast(app, {"type": "dump"})

asyncio.run(main())
```

Brett starts a test meeting in the Snoop profile, turns captions on (CC), runs `uv run python -m spikes.p2_capture`, says two lines, presses Enter. A second device (phone, as a guest or as Jeremy) says one line, Enter again.
Expected: two `/tmp/snoop-caption-dom-*.html` files containing the spoken words and speaker names. If the file says `NO-CAPTION-REGION`, use Chrome DevTools on the Meet tab to find the caption container (search the Elements panel for a spoken word), update the selector in `captionRegionHTML()`, reload the extension, and retry. Record the selector in findings.

- [ ] **Step 2: Build a sanitized fixture** — copy the captured structure to `spikes/extension/test/fixture_captions.html`, replacing every real name with `Test Speaker A` / `Test Speaker B` and every caption sentence with `yo snoop how many prs merged` / `we should snoop around the logs`. Keep the element structure, attributes and class names exactly. Delete the `/tmp` captures: `rm -f /tmp/snoop-caption-dom-*.html`.

- [ ] **Step 3: Sanitization guard — failing test, then pass**

```python
# spikes/test_fixture_is_sanitized.py
import json, pathlib

def test_fixture_contains_no_roster_names_or_emails():
    html = pathlib.Path("spikes/extension/test/fixture_captions.html").read_text()
    team = json.loads(pathlib.Path("config/team.json").read_text())
    for m in team["members"]:
        for token in [m["email"], *m["display_name"].split()]:
            assert token.lower() not in html.lower(), f"real identity in fixture: {token}"
    assert "@" not in html
```

Run it before Step 2's edits are complete (with the raw capture copied in) and confirm it FAILS naming a real name; after sanitizing, it PASSES.

- [ ] **Step 4: Parser — failing Node test**

```json
// spikes/extension/package.json
{"name": "snoop-spike-extension", "private": true, "type": "module",
 "scripts": {"test": "node --test test/"}, "devDependencies": {"jsdom": "^25.0.0"}}
```

```js
// spikes/extension/test/caption_parse.test.mjs
import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {JSDOM} from "jsdom";
import {createRequire} from "node:module";
const require = createRequire(import.meta.url);
const {parseCaptions} = require("../caption_parse.js");

test("parses speaker and text from the sanitized Meet fixture", () => {
  const dom = new JSDOM(readFileSync(new URL("./fixture_captions.html", import.meta.url), "utf8"));
  const lines = parseCaptions(dom.window.document.body);
  assert.deepEqual(lines, [
    {speaker: "Test Speaker A", text: "yo snoop how many prs merged"},
    {speaker: "Test Speaker B", text: "we should snoop around the logs"},
  ]);
});
```

Add `spikes/extension/node_modules/` to `.gitignore` first (jsdom is a dev-only dependency).

Run: `cd spikes/extension && npm install && npm test`
Expected: FAIL (`Cannot find module '../caption_parse.js'`).

- [ ] **Step 5: Parser — implement from the fixture's real structure, then green**

Write `spikes/extension/caption_parse.js` defining `function parseCaptions(root)` using the selectors found in Step 1 (speaker-name element and text element inside each caption block), returning `[{speaker, text}]` in document order, trimming whitespace; end the file with:

```js
if (typeof module !== "undefined") module.exports = {parseCaptions};
```

The selectors are only known after Step 1; record them as constants at the top of the file (`const CAPTION_BLOCK = "...", SPEAKER = "...", TEXT = "...";`) and in findings.
Run: `cd spikes/extension && npm test`
Expected: 1 PASS.

- [ ] **Step 6: Wire it live** — in `content.js`, add a `MutationObserver` on the caption region that calls `parseCaptions` and `emitCaption(speaker, text)` for each new or changed final line (de-duplicate by `speaker+text`). Add `caption_parse.js` before `content.js` in the manifest's isolated content script list; re-run `uv run pytest spikes/test_extension_manifest.py` (must stay green).

```python
# spikes/p2_listen.py
"""Log caption events from the extension with receipt time and wake/stop flags."""
import asyncio, json, time
from aiohttp import web
from spikes.bridge_server import make_app
from spikes.common import SECRETS_DIR, pdt_now
from spikes.p2_wake import is_wake, is_stop

LOG = "/tmp/p2-events.ndjson"

def on_message(m):
    if m.get("type") != "caption":
        return
    rec = {"recv_epoch": time.time(), "speaker": m["speaker"], "text": m["text"],
           "wake": is_wake(m["text"]), "stop": is_stop(m["text"])}
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(pdt_now(), f"wake={rec['wake']} stop={rec['stop']}", m["speaker"], "|", m["text"][:100])

async def main():
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), on_message)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    await asyncio.Future()

asyncio.run(main())
```

- [ ] **Step 7: Live wake run (Brett + one other person)** — Snoop profile in the meeting with captions on; run `uv run python -m spikes.p2_listen`. The **other person** reads `spikes/p2_script.txt` while Brett runs `uv run python spikes/p2_mark.py` and presses Enter at the end of each line they say.
Compute per line: latency = first caption event containing the line's words − `end_epoch`. Pass bars: caption p90 ≤ 2.0 s; wake recall ≥ 18/20; **0/10 decoys trigger**; "peanut butter" detected on the last line; speaker name equals the reader's Meet name on ≥ 29/30 lines. Afterwards: `rm -f /tmp/p2-events.ndjson /tmp/p2-marks.ndjson` once numbers are in findings.

- [ ] **Step 8: Verdict and commit**

```bash
git rm spikes/p2_receiver.py
git add spikes/p2_capture.py spikes/p2_listen.py spikes/test_fixture_is_sanitized.py spikes/extension docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P2 caption reading in the extension"
```

---

### Task 7: Probe P4 — Snoop's voice and card through the extension; BlackHole fallback (§8.4)

**Files:**
- Create: `spikes/p4_media.py`
- Delete: `spikes/p6_audio_stop.py` (Attendee websocket version — obsolete)
- Modify (fallback only): `pyproject.toml` (add `sounddevice`)

**Interfaces:**
- Consumes: Task 5 bridge + `page_media.js`
- Produces (findings): whether Meet uses the injected mic and camera; measured stop latency for the extension path and, if needed, BlackHole.

- [ ] **Step 1: Write the media probe** — uses macOS `say` for audio so no Google key is needed.

```python
# spikes/p4_media.py
"""Speak a long `say` paragraph into the meeting through the extension; Enter sends stop.
Fallback: --blackhole plays the same audio to the BlackHole device instead."""
import argparse, asyncio, base64, subprocess, sys, time, wave, tempfile
from aiohttp import web
from spikes.bridge_server import make_app, broadcast
from spikes.common import SECRETS_DIR, pdt_now

RATE = 24000
TEXT = "Snoop here. Aight, peep this. This is a long test so we can time how fast the audio stops. " * 6

def pcm() -> bytes:
    with tempfile.TemporaryDirectory() as d:
        out = f"{d}/s.wav"
        subprocess.run(["say", "-o", out, f"--data-format=LEI16@{RATE}", "--file-format=WAVE", TEXT], check=True)
        with wave.open(out) as w:
            return w.readframes(w.getnframes())

async def via_extension():
    app = make_app((SECRETS_DIR / "bridge-token").read_text(), lambda m: None)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8790).start()
    input("extension connected and in the meeting? press Enter to start talking ")
    data = pcm(); step = RATE * 2  # 1 s chunks
    loop = asyncio.get_running_loop()
    stop = loop.run_in_executor(None, input, "talking; press Enter to stop\n")
    for i in range(0, len(data), step):
        if stop.done():
            break
        await broadcast(app, {"type": "audio", "pcm_b64": base64.b64encode(data[i:i+step]).decode(), "rate": RATE})
        await asyncio.sleep(0.9)  # stay ~0.1 s ahead of playback, never far ahead
    await stop
    await broadcast(app, {"type": "stop"})
    print(pdt_now(), "STOP SENT", time.time())
    await asyncio.sleep(5)

def via_blackhole():
    import numpy as np, sounddevice as sd
    data = np.frombuffer(pcm(), dtype="<i2")
    sd.play(data, RATE, device="BlackHole 2ch")
    input("talking; press Enter to stop\n")
    sd.stop(); print(pdt_now(), "STOP SENT", time.time())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--blackhole", action="store_true")
    a = ap.parse_args()
    via_blackhole() if a.blackhole else asyncio.run(via_extension())
```

- [ ] **Step 2: Positive control — card and voice visible to others** — Brett joins a test meeting in the Snoop profile (the extension is active from page load); Jeremy or Lindsay joins from their own device. Run `uv run python -m spikes.p4_media`. Expected: the other person sees the **"Snoop (Brett Evans)"** card as Brett's video and hears the `say` voice.
- [ ] **Step 3: Negative control — the real mic is not used** — while the probe is idle, Brett speaks near the laptop. Expected: the other person hears **nothing** from Brett's tile. If they hear Brett, Meet is bypassing the injected stream — record FAILS for the extension path and go to Step 6.
- [ ] **Step 4: Stop latency** — the other person screen-records their device with audio. Brett presses Enter ~5 s into speech. From the recording, measure STOP SENT → silence. Pass bar: ≤ 1.0 s. Repeat 3 times; record each.
- [ ] **Step 5: Device switch robustness** — in Meet's settings, change microphone and camera selection and back. Expected: Snoop's voice and card persist (Meet re-calls `getUserMedia`; the override must answer again). Record the result.
- [ ] **Step 6: BlackHole fallback (only if Steps 2–4 fail)** — Brett installs BlackHole (`brew install --cask blackhole-2ch`, admin password typed by Brett), adds `sounddevice` and `numpy` with `uv add sounddevice numpy`, selects "BlackHole 2ch" as the microphone in the Snoop profile's Meet settings, and runs `uv run python -m spikes.p4_media --blackhole`. Repeat Steps 2–4 (card is unavailable on this path; record it).
- [ ] **Step 7: Verdict and commit** — HOLDS if either path passes Steps 2–4; record which path Plan 2 uses (D29).

```bash
git rm spikes/p6_audio_stop.py
git add spikes/p4_media.py pyproject.toml uv.lock docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P4 voice and card via extension (BlackHole fallback)"
```

---

### Task 8: Probe P5 — Chat app limited to the team group and one space (§8.5)

**Files:**
- Reuse: `spikes/p5_chat_post.py` (written; credentials load inside `main()`)
- Modify: findings (P5 row)

**Interfaces:**
- Consumes: Task 2 Cloud project and Google Group; a Chat-app service-account key at `spikes/.secrets/chat-key.json`
- Produces (findings): whether visibility can be limited to the group, and the exact error when posting to a space the app is not in.

- [ ] **Step 1: Configure the Chat app (Brett, Cloud console)** — Google Chat API → Configuration: name `Snoop`, no interactive features, **Visibility: specific people and groups → `snoop-team@startup.ai`**. Create service account `snoop-chat`, download key to `spikes/.secrets/chat-key.json`, `chmod 600`. In Chat, create space `Snoop`, add the group's members and the app. Create a second space `Snoop-decoy` **without** the app.
- [ ] **Step 2: Run**

Run: `uv run python -m spikes.p5_chat_post spaces/<snoop-space> spaces/<decoy-space> users/<brett-id>`
Expected: `positive ('OK', ...)` and the message appears in `Snoop` with Brett @-mentioned; `negative ('HTTP 403' or 'HTTP 404', ...)` and nothing appears in `Snoop-decoy`. If a saasless user outside the group exists, they search for the app in Chat and cannot find it — record result or "no such user to test".
- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P5 Chat app scope"
```

---

### Task 9: Probes P6 + P7 — own-voice exclusion and two-Snoop detection (§8.6, §8.7)

**Files:**
- Create: `spikes/p7_seats.py`, `spikes/test_p7_seats.py`
- Modify: findings

**Interfaces:**
- Consumes: `spikes.roster` (Task 5); Task 6 live caption events; Task 7 media probe
- Produces: `is_own_seat(speaker: str, own_label: str) -> bool`; `stand_down(my_email: str, speaker: str, text: str, roster: Roster) -> bool` — True when another roster member's seat says "Snoop here" and that member has a **lower** `host_priority` number than mine (higher priority).

- [ ] **Step 1: Failing tests**

```python
# spikes/test_p7_seats.py
from spikes.p7_seats import is_own_seat, stand_down
from spikes.roster import load

R = load("config/team.json")

def test_own_seat_is_exact_label_only():
    assert is_own_seat("You", "You")
    assert not is_own_seat("Brett Evans", "You")  # the host on another device is a real participant

def test_lower_priority_snoop_stands_down():
    assert stand_down("jeremy@startup.ai", "Brett Evans", "Snoop here, CI is green", R)

def test_higher_priority_snoop_stays():
    assert not stand_down("brett@startup.ai", "Jeremy Leeds", "Snoop here, CI is green", R)

def test_ordinary_speech_never_triggers_stand_down():
    assert not stand_down("jeremy@startup.ai", "Brett Evans", "I think snoop here is fine", R)

def test_non_roster_speaker_never_triggers_stand_down():
    assert not stand_down("jeremy@startup.ai", "Some Guest", "Snoop here, hi", R)
```

Run: `uv run pytest spikes/test_p7_seats.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Implement, then green**

```python
# spikes/p7_seats.py
import re
from spikes.roster import Roster

_SNOOP_HERE = re.compile(r"^\W*snoop\W+here\b", re.IGNORECASE)

def is_own_seat(speaker: str, own_label: str) -> bool:
    return speaker == own_label

def stand_down(my_email: str, speaker: str, text: str, roster: Roster) -> bool:
    if not _SNOOP_HERE.search(text):
        return False
    me = roster.by_email(my_email)
    others = roster.by_display_name(speaker)
    if me is None or len(others) != 1:
        return False
    return others[0].host_priority < me.host_priority
```

Run: `uv run pytest spikes/test_p7_seats.py -v`
Expected: 5 PASS

- [ ] **Step 3: Live — own-voice label (Brett + one person)** — run `spikes.p2_listen` and `spikes.p4_media` together (both use port 8790: start `p2_listen` on 8790 and change `p4_media`'s port to 8791 with a second `make_ext_config` port only if they conflict — record what you did). Expected: caption events for Snoop's own `say` speech arrive with a speaker label; record the exact label (e.g. `You`). That label becomes `own_label`. Pass: every own-speech line carries that label and no other speaker's line does.
- [ ] **Step 4: Live — another seat says "Snoop here"** — Jeremy or Lindsay says "Snoop here, testing" from their own seat. Expected: a caption event with their Meet display name and text starting "Snoop here"; `stand_down("brett@startup.ai", <name>, <text>, R)` is False for Brett (higher priority) and would be True if Brett's priority were lower — record the raw event.
- [ ] **Step 5: Commit**

```bash
git add spikes/p7_seats.py spikes/test_p7_seats.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P6/P7 own-voice label and two-Snoop detection"
```

---

### Task 10: Close out — stop or go, clean up

**Files:**
- Modify: findings (summary + cleanup log)

- [ ] **Step 1: Summarize** — every row in the findings table has a verdict, evidence and a "consequence for Plans 1–2" line (P1–P7). Add `## Stop or go`: **GO only if** P1 Run A HOLDS, P2 caption reading HOLDS, and P4 HOLDS on at least one path. List every spec change the findings force (e.g. organizer-only participant reads, BlackHole instead of injection, a different own-voice label).
- [ ] **Step 2: Clean up**

```bash
cd ~/Code/Saasless/yo-snoop && rm -f spikes/.secrets/chat-key.json spikes/.secrets/token-*.json /tmp/snoop-caption-dom-*.html /tmp/p2-*.ndjson && ls spikes/.secrets
df -h /System/Volumes/Data | tail -1
```

Revoke the deleted service-account key in the Cloud console. Keep `client_secret.json` and `bridge-token` only if Plan 2 development continues within a week; otherwise delete and record. Record what was kept and why.

- [ ] **Step 3: Full suite, commit, push**

Run: `uv run pytest -q && (cd spikes/extension && npm test)`
Expected: all pass.

```bash
git add docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "findings: Plan 0 stop/go and cleanup"
git push
```
