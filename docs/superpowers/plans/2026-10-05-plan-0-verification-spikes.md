# Snoop Plan 0 — Verification Spikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove or disprove the spec's unverified claims (§8) plus one integration risk the spec depends on, before any product code is written.

**Architecture:** Each probe is a small, throwaway Python script under `spikes/` plus a manual procedure, producing a verdict (HOLDS / FAILS / PARTIAL) with pasted evidence in one findings file. Probes that need Google admin actions are performed by the owner (Brett); scripts only read and measure. A FAILS on Probe 1 or Probe 4 stops the program and returns to the spec.

**Tech Stack:** Python 3.12 via `uv`; `google-api-python-client`, `google-auth-oauthlib`, `google-cloud-texttospeech`, `aiohttp`, `websockets`, `claude-agent-sdk`; Claude Code CLI 2.1.283 (installed); self-hosted Attendee (Docker); Google Workspace Admin console and Google Cloud console (UI — `gcloud` is not installed on this Mac).

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` (D1–D23). Read §3, §4, §5 and §8 before starting.

## Roadmap (this plan is 1 of 4)

| Plan | Scope | Written when |
|---|---|---|
| **0 (this)** | Verify §8 claims + audio-stop latency | now |
| 1 | Mac brain: installer, `snoop` user + negative controls, owner refresher (clone, PR/CI file, repo map, `AGENT_C_HOME` bundle), Claude Code sandbox config, Serena lockdown, registry-mcp, answer gate, streaming brain server | after Plan 0 findings |
| 2 | VM conductor: wake/stop/mute, room + asker checks, pacing chunker, pre-loading, brain routing, Pipecat pipeline, Attendee client, Chat poster | after Plan 0 findings |
| 3 | Workspace production setup runbook + end-to-end rehearsal (spec §9) | after Plans 1–2 |

Plans 1 and 2 are written from Plan 0's findings, not before: every §8 claim changes their code (which token the room check uses, which Claude Code flags exist, how audio is cut).

## Global Constraints

- Internal tool for Brett, Jeremy, Lindsay only; never customer-facing (D1, §7).
- Attendee never signs in as brett@ (or any human's account); the bot identity is agent-c@ only. brett@ may be used only as a read-only Meet organizer in P1 (D24).
- No secret is ever printed through a tool, committed, or pasted into findings. Compare secrets by sha256 prefix only. Key files live in `spikes/.secrets/` (gitignored) and are deleted at the end of Plan 0.
- `agent-c@startup.ai` must never send email, use Meet in-meeting chat, or post anywhere but the one Chat space (D17). No probe calls Attendee's `send_chat_message` endpoint.
- Every gate probe has a **negative control** (a case that must fail) and a **positive control** (a case that must succeed), and both are recorded. A probe whose negative control cannot fail is not evidence.
- Times in findings are Pacific (PDT), labeled.
- Disk: this Mac had 46 GiB free on 2026-10-05. Check `df -h /System/Volumes/Data` before Docker work; stop if under 30 GiB. Prune Attendee images at the end (Task 8).
- Python 3.12 (not the system 3.14) — pinned in `pyproject.toml`.

## Review Focus

1. **Brett's own sign-in hijacked by the bot's SSO profile** — if the legacy SAML profile is not truly OU-scoped, the Attendee signing key could sign in as brett@. Expected: brett@ and jeremy@ still get Google's password page. Pinned in Task 5, Step 6.
2. **An anonymous joiner shows up late in the participant list** — if the Meet REST list lags, Snoop speaks to a room that already has an outsider. Expected: first appearance within the measured bound, recorded p90. Pinned in Task 4, Step 5.
3. **"Peanut butter" cannot actually stop the audio fast** — Attendee may have already buffered seconds of speech. Expected: audio ends ≤ 1.0 s after we stop sending. Pinned in Task 7, Step 4.
4. **Mid-sentence "snoop" triggers the bot** — decoy phrases must not match. Expected: 0 of 10 decoys trigger. Pinned in Task 6, Step 5.
5. **A denied Claude Code tool silently runs anyway** — the harness must detect a write that happened. Expected: positive control proves detection works; write and network prompts leave no trace. Pinned in Task 3, Steps 3–4.

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

### Task 2: Owner setup — Workspace and Google Cloud prerequisites (manual, Brett)

These are admin-console actions. The executor guides; Brett clicks. Nothing here is scripted because it needs super-admin rights.

**Files:**
- Modify: `docs/superpowers/findings/2026-10-plan-0-findings.md` (append "Setup log")

**Interfaces:**
- Produces: OU `/Snoop Bot`; user `agent-c@startup.ai` (non-admin, in `/Snoop Bot`); Google Cloud project `yo-snoop` with Meet REST API, Google Chat API, People API, Cloud Text-to-Speech API enabled; OAuth consent screen **Internal**; one OAuth client of type **Desktop**, downloaded to `spikes/.secrets/client_secret.json`.

- [ ] **Step 1: Create the OU and user** — Admin console → Directory → Organizational units → create `Snoop Bot`. Users → add `agent-c@startup.ai`, first name `Snoop`, OU `Snoop Bot`, **no admin role**.
- [ ] **Step 2: Turn off services for the OU** — Apps → Google Workspace: for OU `Snoop Bot` set **Gmail, Drive and Docs** OFF. Leave Meet, Chat, Calendar ON. Calendar → sharing settings for the OU: external sharing off. (Calendar RSVP behavior is handled in Plan 2 by never calling RSVP APIs.)
- [ ] **Step 3: Complete the bot's first sign-in** — in a private window sign in as `agent-c@`, finish the "Welcome to Google Workspace" flow, set language to English (United States) at `myaccount.google.com/personal-info` (Attendee requires both).
- [ ] **Step 4: Create the Cloud project** — console.cloud.google.com → new project `yo-snoop` under the saasless.ai organization. Enable: Google Meet REST API, Google Chat API, People API, Cloud Text-to-Speech API. OAuth consent screen: **Internal**. Credentials → OAuth client ID → Desktop app → download JSON to `~/Code/Saasless/yo-snoop/spikes/.secrets/client_secret.json`.
- [ ] **Step 5: Verify without printing secrets**

Run: `ls -l ~/Code/Saasless/yo-snoop/spikes/.secrets/ && git -C ~/Code/Saasless/yo-snoop status --porcelain spikes/.secrets`
Expected: `client_secret.json` listed; the `git status` line prints nothing (ignored).

- [ ] **Step 6: Record and commit** — append to findings under `## Setup log`: date/time (PDT), each item done, by whom. No IDs that are secrets (project ID is fine).

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

- [ ] **Step 6: API key helper probe (Brett stores the key; never printed)**

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

- [ ] **Step 5: Live run A — as organizer (brett@)**

Brett creates a Meet from brett@ calendar. Start: `uv run python -m spikes.p1_meet_participants --code <code> --as brett`. Sign in via the browser that opens as brett@. Then, noting the clock (PDT) at each click:
1. Join from a **private window, not signed in** (anonymous). 2. Join from jeremy@ or lindsay@ (or a second saasless account). 3. Dial in by phone if available. 4. Leave each.

Expected per event: a line with the right `kind`; for saasless users an `@startup.ai` email; time from click to line recorded. **Compute p50/p90 join-to-appearance across ≥ 5 joins.** Pass bar for HOLDS: anonymous joiner appears within 10 s p90 (Plan 2 adds Attendee's instant join webhook as a trigger, so this bounds the worst case).

- [ ] **Step 6: Live run B — as the bot (agent-c@), not the organizer**

Same meeting; delete nothing; run `--as agentc` and sign in as agent-c@ (the bot account must be **in** the meeting — join it from a private window as agent-c@).
Expected (record whichever happens): participants listed → the bot can be its own principal; `LIST-ERROR`/empty → organizer token required. **Spec D24 makes this decisive:** meetings may be organized by Brett, Jeremy or Lindsay, so an organizer-only answer means Plan 2 holds a read-only `meetings.space.readonly` token for each of the three, and a meeting organized by anyone else cannot be room-checked (Snoop would treat it as mixed). Repeat Run A with Jeremy or Lindsay as organizer if they are available, to confirm the result is not specific to Brett. Also record whether `email_for` resolves emails as agent-c@ (directory sharing) or errors.

- [ ] **Step 7: Verdict and commit** — P1 HOLDS if a principal Plan 2 can hold on the VM sees live participants with kind + resolvable saasless identity within the bar. Record which principal. FAILS → stop; return to spec owner.

```bash
git add spikes/p1_meet_participants.py spikes/test_p1_classify.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P1 Meet participants principal and latency"
```

---

### Task 5: Probe P4 — Attendee SAML sign-in, OU-scoped, with negative control (§8.4)

**Files:**
- Create: `spikes/p4_attendee/docker-compose.override.yml` (only if needed for hostname)
- Modify: findings (P4 row + evidence)

**Interfaces:**
- Produces: a running self-hosted Attendee instance with a Google Meet bot login group `snoop` for agent-c@, reused by Tasks 6 and 7. Attendee API token stored in `spikes/.secrets/attendee-token` (mode 600).

- [ ] **Step 1: Disk and Docker check**

Run: `df -h /System/Volumes/Data | tail -1; docker info --format '{{.ServerVersion}}'`
Expected: ≥ 30 GiB free and a server version. If Docker prints nothing, start Docker Desktop first.

- [ ] **Step 2: Run Attendee self-hosted, pinned**

```bash
cd ~/Code/Saasless/yo-snoop/spikes && git clone https://github.com/attendee-labs/attendee.git p4_attendee/src
cd p4_attendee/src && git rev-parse HEAD
```

Record the commit SHA in findings (this is the version Plan 2 pins). Follow its README "Running in development mode" section exactly; create an account and API key in the local UI; save the token: `pbpaste > ../../.secrets/attendee-token && chmod 600 ../../.secrets/attendee-token && pbcopy < /dev/null`.

**Hostname note:** Google redirects the bot's browser (inside Attendee's container) to the SSO sign-in URL. If `localhost` does not resolve from inside the container, stop and record "needs reachable HTTPS hostname"; Plan 2 then runs this on the VM behind TLS. Do not expose the Mac to the internet to work around it.

- [ ] **Step 3: Create the signing key and cert (Brett)**

```bash
cd ~/Code/Saasless/yo-snoop/spikes/.secrets && openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -sha256 -days 3650 -nodes -subj "/CN=snoop-bot-sso" && chmod 600 key.pem
```

- [ ] **Step 4: Legacy SSO profile (Brett, Admin console)** — Security → Authentication → SSO with third-party IdP → Add SAML profile → "Legacy SSO profile": enable; Sign-in URL `https://<attendee-host>/bot_sso/google_meet_sign_in`; Sign-out URL `https://<attendee-host>/bot_sso/google_meet_sign_out`; domain-specific issuer **Yes**; upload `cert.pem`. Save.

- [ ] **Step 5: Assign the profile to OU `Snoop Bot` ONLY** — Manage SSO profile assignments → select OU `Snoop Bot` → legacy profile. **Confirm the root OU and every other OU still show "None".** Screenshot that page (no secrets on it) into findings.

- [ ] **Step 6: Negative control — the profile must not touch anyone else**

In a fresh private window, start sign-in as **brett@startup.ai** at accounts.google.com.
Expected: Google's own password page. **If the browser is redirected to the Attendee URL, STOP: P4 FAILS.** Immediately set the assignment back to None and record it. Repeat for jeremy@ or lindsay@.

- [ ] **Step 7: Positive control — the bot signs in**

In the Attendee UI: Settings → Bot Logins → Google Meet → create group `snoop`, add login (email agent-c@startup.ai, upload key.pem and cert.pem). Create a bot via API into a test meeting with `"google_meet_settings": {"use_login": true, "login_group_name": "snoop"}`:

The token goes in a header file written by the `printf` builtin, so it never appears in any process's arguments:

```bash
cd ~/Code/Saasless/yo-snoop/spikes/.secrets && printf 'Authorization: Token %s\n' "$(cat attendee-token)" > attendee-header && chmod 600 attendee-header
```

```bash
curl -s -X POST http://localhost:8000/api/v1/bots -H @$HOME/Code/Saasless/yo-snoop/spikes/.secrets/attendee-header -H 'Content-Type: application/json' -d '{"meeting_url":"https://meet.google.com/<code>","bot_name":"Snoop","google_meet_settings":{"use_login":true,"login_group_name":"snoop"}}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id"), d.get("state"))'
```

Expected: bot joins showing as "Snoop" (not "Unverified"/anonymous). Never add `-v` to curl (it prints headers). Tasks 6 and 7 create bots the same way with `-H @…/attendee-header`.

- [ ] **Step 8: Verdict, alternative, commit** — HOLDS only if Step 6 negative passed for two non-bot users AND Step 7 positive passed. Record also, as an owner decision for Plan 2: Attendee's docs recommend a **separate** Workspace for the bot (subdomain), which removes the "key signs in as Brett" risk entirely rather than scoping it.

```bash
git add docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P4 Attendee SAML sign-in OU-scoped"
```

---

### Task 6: Probe P2 — caption latency, wake accuracy, speech events (§8.2)

**Files:**
- Create: `spikes/p2_wake.py`
- Test: `spikes/test_p2_wake.py`
- Create: `spikes/p2_receiver.py`
- Create: `spikes/p2_script.txt`
- Create: `spikes/p2_mark.py`
- Modify: findings

**Interfaces:**
- Consumes: Task 5's Attendee instance and bot login
- Produces: `spikes.p2_wake.is_wake(text: str) -> bool` and `spikes.p2_wake.is_stop(text: str) -> bool` — first drafts of the matchers Plan 2 hardens.

- [ ] **Step 1: Write the failing test**

```python
# spikes/test_p2_wake.py
import pytest
from spikes.p2_wake import is_wake, is_stop

@pytest.mark.parametrize("t", ["Yo Snoop, how many PRs merged?", "yo snoop what's CI",
                               "You Snoop, status?", "Yo, Snoopy, any blockers?", "  yo snoop"])
def test_wake_hits(t):
    assert is_wake(t)

@pytest.mark.parametrize("t", ["we should snoop around the logs", "yo can you snoop that",
                               "Snoop Dogg is great", "I said yo snoop earlier", "snoop"])
def test_wake_decoys(t):
    assert not is_wake(t)

@pytest.mark.parametrize("t", ["peanut butter", "Peanut butter!", "ok peanut butter please"])
def test_stop_anywhere(t):
    assert is_stop(t)

def test_stop_not_partial():
    assert not is_stop("peanut")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest spikes/test_p2_wake.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# spikes/p2_wake.py
import re

_WAKE = re.compile(r"^\W*(yo|you|yoh|yeah)\W+snoop(y|s)?\b", re.IGNORECASE)
_STOP = re.compile(r"\bpeanut\W+butter\b", re.IGNORECASE)

def is_wake(text: str) -> bool:
    return bool(_WAKE.search(text))

def is_stop(text: str) -> bool:
    return bool(_STOP.search(text))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest spikes/test_p2_wake.py -v`
Expected: all PASS. (Note: "yo can you snoop that" must not match because `can` sits between `yo` and `snoop`.)

- [ ] **Step 5: Live measurement**

Receiver:

```python
# spikes/p2_receiver.py
"""Log Attendee webhooks with PDT receipt time. Run: uv run python -m spikes.p2_receiver"""
import json, time
from aiohttp import web
from spikes.common import pdt_now
from spikes.p2_wake import is_wake

LOG = open("/tmp/p2-events.ndjson", "a")

async def hook(req):
    body = await req.json()
    rec = {"recv_epoch": time.time(), "recv_pdt": pdt_now(), "trigger": body.get("trigger"), "data": body.get("data")}
    txt = json.dumps(body.get("data", {}))
    rec["wake_in_text"] = is_wake(body.get("data", {}).get("transcription", {}).get("transcript", "") if isinstance(body.get("data"), dict) else "")
    LOG.write(json.dumps(rec) + "\n"); LOG.flush()
    print(rec["recv_pdt"], rec["trigger"], txt[:160])
    return web.Response(text="ok")

app = web.Application(); app.router.add_post("/hook", hook)
web.run_app(app, port=8787)
```

Marker (speaker presses Enter at the end of each spoken line):

```python
# spikes/p2_mark.py
import json, time
lines = [l.strip() for l in open("spikes/p2_script.txt") if l.strip()]
with open("/tmp/p2-marks.ndjson", "a") as out:
    for l in lines:
        input(f"SAY: {l}\n  (press Enter when you finish) ")
        out.write(json.dumps({"line": l, "end_epoch": time.time()}) + "\n")
```

`spikes/p2_script.txt` — 20 wake lines then 10 decoys, interleaved in this order:

```
Yo Snoop, how many PRs merged yesterday?
we should snoop around the logs later
Yo Snoop, is CI green on main?
Snoop Dogg had a new album out
You Snoop, what's blocking the v2 epic?
yo can you snoop that branch
Yo Snoop, how many v1 to v2 gaps are missing?
I said yo snoop earlier but never mind
Yo, Snoopy, where is multi-model support?
let's not snoop on Jeremy's branch
Yo Snoop, what did the last run cost?
snoop
Yo Snoop, who opened the newest PR?
the snoop thing is cool
Yo Snoop, which stage is Foodious at?
we could snoop the dashboard
Yo Snoop, any open blockers?
snooping is not a feature
Yo Snoop, summarize today's merges.
don't snoop
Yo Snoop, how does the accessibility review run in v2?
Yo Snoop, what changed in registry-mcp this week?
Yo Snoop, is the AC-v2 branch ahead of main?
Yo Snoop, how many backlog items moved yesterday?
Yo Snoop, what's the newest commit on main?
Yo Snoop, list open PRs.
Yo Snoop, did the verify recipe pass?
Yo Snoop, what's AGNTC-1252 about?
Yo Snoop, what is D17 in the spec?
Yo Snoop, peanut butter.
```

Configure an Attendee webhook (UI) to `http://host.docker.internal:8787/hook` with triggers `transcript.update` and `participant_events.speech_start_stop`. Create a bot with `"transcription_settings": {"meeting_closed_captions": {"google_meet_language": "en-US"}}` plus the login settings from Task 5. Run receiver and marker; read the script aloud.

Compute per line: latency = first `transcript.update` containing the line's words − `end_epoch`; and `speech_stop` event − `end_epoch`. Pass bars: caption p90 ≤ 2.0 s; wake recall ≥ 18/20 on the 20 wake lines; **0/10 decoys trigger**; "peanut butter" detected on the last line.

- [ ] **Step 6: Verdict and commit**

```bash
git add spikes/p2_*.py spikes/test_p2_wake.py spikes/p2_script.txt docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P2 caption latency and wake accuracy"
```

---

### Task 7: Probe P6 — audio output and stop latency (unlisted risk behind D6)

Not in spec §8, but D6 ("peanut butter" cuts audio ~1 s) depends on it: if Attendee buffers seconds of audio we've already sent, the stop is slow no matter what the Conductor does.

**Files:**
- Create: `spikes/p6_audio_stop.py`
- Modify: findings

**Interfaces:**
- Consumes: Task 5 Attendee; Google TTS (Cloud project from Task 2, service account key at `spikes/.secrets/tts-key.json`)
- Produces (findings): measured stop latency; whether Plan 2 must pace chunk sending to keep the buffer short.

- [ ] **Step 1: Write the probe** — a websocket server that Attendee connects to (bot created with `websocket_settings.audio.url`), streams 20 s of Google TTS PCM at 16 kHz in 100 ms chunks, and stops sending at a keypress, logging the stop time.

```python
# spikes/p6_audio_stop.py
"""Run, create a bot with websocket_settings.audio.url=ws://host.docker.internal:8788,
press Enter while it talks; a listener on a second device notes when sound stops."""
import asyncio, base64, json, os, sys, time
import websockets
from google.cloud import texttospeech
from spikes.common import SECRETS_DIR, pdt_now

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SECRETS_DIR / "tts-key.json")
TEXT = ("Aight, peep this. This is a long test paragraph so we can measure how fast "
        "the audio stops. ") * 8
RATE = 16000
CHUNK = RATE * 2 // 10  # 100 ms of 16-bit mono

def synth() -> bytes:
    c = texttospeech.TextToSpeechClient()
    r = c.synthesize_speech(input=texttospeech.SynthesisInput(text=TEXT),
                            voice=texttospeech.VoiceSelectionParams(language_code="en-US"),
                            audio_config=texttospeech.AudioConfig(
                                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                                sample_rate_hertz=RATE))
    return r.audio_content[44:]  # strip WAV header

async def handler(ws):
    pcm = synth()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_reader(sys.stdin, stop.set)
    print("talking; press Enter to stop")
    for i in range(0, len(pcm), CHUNK):
        if stop.is_set():
            print(pdt_now(), "STOP SENT at", time.time()); break
        await ws.send(json.dumps({"trigger": "realtime_audio.bot_output",
                                  "data": {"chunk": base64.b64encode(pcm[i:i+CHUNK]).decode(),
                                           "sample_rate": RATE}}))
        await asyncio.sleep(0.1)  # real-time pacing: never run ahead of playback
    await asyncio.sleep(10)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8788):
        await asyncio.Future()

asyncio.run(main())
```

- [ ] **Step 2: Paced run** — join the test meeting from a second device (phone) as a listener and screen-record it with audio. Run the probe, create the bot, press Enter ~8 s in.
- [ ] **Step 3: Burst run** — change `await asyncio.sleep(0.1)` to `await asyncio.sleep(0)` (sends all audio immediately), rerun, press Enter at ~8 s of heard audio. Revert after.
- [ ] **Step 4: Measure** — from the phone recording, time from the STOP SENT timestamp to silence, for both runs. Pass bar: paced run ≤ 1.0 s. The burst run shows how much Attendee buffers; if it plays to the end, Plan 2 **must** pace sends in real time (record this as a hard requirement).
- [ ] **Step 5: Commit**

```bash
git add spikes/p6_audio_stop.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P6 audio stop latency"
```

---

### Task 8: Probe P5 — Chat app limited to one space and three users (§8.5), then close out

**Files:**
- Create: `spikes/p5_chat_post.py`
- Modify: findings (P5 row, summary, cleanup log)

**Interfaces:**
- Consumes: Task 2 Cloud project; a Chat-app service account key at `spikes/.secrets/chat-key.json`
- Produces (findings): whether the app can be restricted to the three users, and the exact error when posting to a space it is not in.

- [ ] **Step 1: Configure the Chat app (Brett, Cloud console)** — Google Chat API → Configuration: name `Snoop`, avatar optional, no interactive features, **Visibility: make available to specific people** → brett@, jeremy@, lindsay@. Create a service account `snoop-chat`, download key to `spikes/.secrets/chat-key.json`, `chmod 600`. In Chat, create space `Snoop` with the three and add the app. Create a second space `Snoop-decoy` **without** the app.

- [ ] **Step 2: Write the probe**

```python
# spikes/p5_chat_post.py
"""Usage: uv run python -m spikes.p5_chat_post spaces/AAA spaces/BBB users/123"""
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from spikes.common import SECRETS_DIR, pdt_now

creds = service_account.Credentials.from_service_account_file(
    str(SECRETS_DIR / "chat-key.json"), scopes=["https://www.googleapis.com/auth/chat.bot"])
chat = build("chat", "v1", credentials=creds)

def post(space: str, text: str):
    try:
        r = chat.spaces().messages().create(parent=space, body={"text": text}).execute()
        return "OK", r.get("name")
    except HttpError as e:
        return f"HTTP {e.resp.status}", str(e)[:200]

good, decoy, user = sys.argv[1], sys.argv[2], sys.argv[3]
print(pdt_now(), "positive", post(good, f"<{user}> P5 probe: Snoop can post here."))
print(pdt_now(), "negative", post(decoy, "P5 probe: this must NOT post."))
```

- [ ] **Step 3: Run**

Run: `uv run python -m spikes.p5_chat_post spaces/<snoop-space> spaces/<decoy-space> users/<brett-id>`
Expected: `positive ('OK', ...)` and the message appears in `Snoop` with Brett @-mentioned; `negative ('HTTP 403' or 'HTTP 404', ...)` and nothing appears in `Snoop-decoy`. Also: a fourth saasless user (if one exists) searches for the app in Chat and cannot find it — record result or "no fourth user to test".

- [ ] **Step 4: Summarize** — fill the findings table: every row has a verdict, evidence, and a "consequence for Plans 1–2" line. Add a final section `## Stop or go` stating: GO only if P1 and P4 HOLD; list every spec change the findings force (e.g., organizer-held Meet token, separate bot Workspace, paced audio sending).

- [ ] **Step 5: Clean up**

```bash
cd ~/Code/Saasless/yo-snoop/spikes && rm -f .secrets/chat-key.json .secrets/tts-key.json .secrets/token-*.json && ls .secrets
docker ps --format '{{.Names}}' | grep -i attendee
df -h /System/Volumes/Data | tail -1
```

Keep `key.pem`/`cert.pem`/`attendee-token` only if the owner chooses to reuse this Attendee instance for Plan 2 development; otherwise delete them and the Docker images (`docker compose down -v` in `p4_attendee/src`, then `docker image prune -f`). Revoke the deleted service-account keys in the Cloud console. Record what was kept and why.

- [ ] **Step 6: Commit and push**

```bash
git add spikes/p5_chat_post.py docs/superpowers/findings/2026-10-plan-0-findings.md
git commit -m "spikes: P5 Chat app scope; Plan 0 findings and stop/go"
git push
```
