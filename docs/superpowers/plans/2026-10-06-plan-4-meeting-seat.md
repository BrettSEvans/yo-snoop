# Snoop Plan 4 — The Meeting Seat Implementation Plan (Phase 1b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Revised 2026-10-09 (desk first, adversarial review).** This is **Phase 1b** (spec D33): start only after Plans 1–3 (Desk Snoop) are done **and** Plan 0's Meet probes (P1, P2, P4–P7) report GO. Changes from the 2026-10-06 version:
> - **Reuse, don't rebuild:** `yosnoop/brain_client.py`, `yosnoop/speech.py` (`shape` → `Shaped(spoken, full)`), `yosnoop/qlog.py` and `yosnoop/wake.py` come from Plan 2. Task 4 below is superseded by Plan 2 Task 4; in Task 5, keep only `chat.py` and `voice.py`; in Task 6, post `shaped.full` to Chat when `len(sentences(g.text)) > 3`; in Task 7, `qlog` already exists.
> - **D41 — the room check fails closed on an empty list** (review defect 1, high). Task 3 adds, before Step 2, this failing test, and `verdict()` and `GoogleMeet._fetch` change as shown:
>
> ```python
> # tests/test_room.py (add)
> def test_empty_or_self_only_room_is_mixed():
>     assert verdict([], R, own_user_id="users/1") == "mixed"
>     assert verdict([B], R, own_user_id="users/1") == "mixed"
> ```
>
> ```python
> # yosnoop/room.py — verdict
> def verdict(participants, roster, own_user_id: str) -> str:
>     others = [p for p in participants if p.user_id != own_user_id]
>     if not others:
>         return "mixed"
>     return "team" if all(_is_team(p, roster) for p in others) else "mixed"
> ```
>
> ```python
> # yosnoop/google_meet.py — paginate both lists; no active record → raise (RoomWatcher turns it into "mixed")
> def _all(collection, key, **kw):
>     req, out = collection.list(**kw), []
>     while req is not None:
>         resp = req.execute()
>         out += resp.get(key, [])
>         req = collection.list_next(req, resp)
>     return out
>
> def _fetch(self, code: str):
>     recs = _all(self.meet.conferenceRecords(), "conferenceRecords",
>                 filter=f'space.meeting_code = "{code}" AND end_time IS NULL')
>     if not recs:
>         raise LookupError("no active conference")
>     out = []
>     for rec in recs:
>         ps = _all(self.meet.conferenceRecords().participants(), "participants", parent=rec["name"])
>         out += [classify(p) for p in ps if not p.get("latestEndTime")]
>     return out
> ```
>
> Add a test with a fake service returning two pages and one returning zero records (→ `RoomWatcher.current()` is `("mixed", [])`).
> - **Emails:** `resolve_email` accepts only an address whose People API source is the domain profile (`metadata.source.type == "DOMAIN_PROFILE"`); anything else → `None` (not team). Add a test with a non-domain source.
> - **`--dev` refuses a live Meet room** (D39): `./snoop start --dev` exits with an explanation if a `meeting` message arrives.

**Goal:** `./snoop start` puts Snoop in the host's Meet seat: it hears "Yo Snoop" questions through the extension, checks the room, asks the brain (Plan 1), and answers by voice (team room) or Chat (mixed room) — Phase 1 scope (spec D33).

**Architecture:** The production extension (`extension/`, promoted from Plan 0's spike) streams captions and the meeting code over the token-gated localhost bridge to the **Conductor** (`yosnoop/conductor/`), which runs as the host. A pure state machine turns caption events into actions (stop, ask, stand down); I/O adapters do the room check (Meet REST + People API with the host's read-only token), talk to the brain process, synthesize speech (Google TTS) and post to Chat. Phase 1 delivery is a small asyncio pipeline (D36).

**Tech Stack:** Python 3.12 (`aiohttp`, `google-api-python-client`, `google-auth-oauthlib`, `google-cloud-texttospeech`; `sounddevice` only if Plan 0 chose BlackHole), Chrome MV3 extension, Node `node --test` + `jsdom` for extension tests.

**Spec:** `docs/superpowers/specs/2026-10-05-yo-snoop-design.md` — D4–D9, D11, D13, D17, D24, D26–D33, D36; §3.1, §4, §5.4, §6. Plans 1–3 must be complete; Plan 0 Meet probes must be GO.

## Inputs from Plan 0 findings (read before Task 1; each has a default)

| Input | Where it comes from | Default if Plan 0 confirms the assumption |
|---|---|---|
| `CAPTION_BLOCK`, `SPEAKER`, `TEXT` selectors | Plan 0 Task 6, `spikes/extension/caption_parse.js` | use the spike file verbatim |
| `VOICE_PATH` | Plan 0 Task 7 verdict | `"extension"`; `"blackhole"` if injection failed |
| `OWN_LABEL` | Plan 0 Task 9 Step 3 | `"You"` |
| Participant principal | Plan 0 Task 4 Run B | host's own token works as a non-organizer; if not, `room.py` already fails closed to `mixed` — record that consequence in the runbook (Plan 3) |

If Plan 0 ended **NO-GO**, do not start this plan.

## Global Constraints

- Phase 1 (D33): spoken answers are at most 3 sentences after "Snoop here"; anything longer is posted in full to Chat. No pre-loading, no pacing check-ins.
- Every spoken answer begins "Snoop here" (D28). The card reads "Snoop (<host display name>)".
- Mixed room or failed room check → Chat only; speak only "Snoop here, sent it to Chat." (D5). Room check fails closed.
- Own-seat captions are ignored (D30). "Peanut butter" from anyone mutes speech until "Yo Snoop" (D6); research and Chat posts continue.
- D32: a lower-priority Snoop that hears another roster seat say "Snoop here" goes passive for the meeting and posts once to Chat.
- The extension's permissions stay `https://meet.google.com/*` only; it never sends Meet chat or keystrokes (tests from Plan 0 carry over).
- Host-side secrets: `~/.config/snoop/secrets/{meet-token.json,tts-key.json,chat-key.json}`; Chat config `~/.config/snoop/chat.json` `{"space": "spaces/…"}`. Never logged.
- Logs: `~/.config/snoop/logs/questions-YYYY-MM-DD.ndjson` — question, asker, room verdict, answer, latency; **never caption text other than the question**; pruned to 7 days at start.

## Review Focus

1. **A guest's caption gets answered aloud** because the room check was stale — expected: the per-sentence re-check catches a join within one sentence. Pinned in Task 6, Step 1.
2. **Snoop answers its own voice** — expected: own-label captions produce no actions. Pinned in Task 2.
3. **Two Snoops both keep answering** — expected: the lower-priority one is passive after the first "Snoop here". Pinned in Task 2.
4. **A Chat post lands in the wrong space** — expected: refused in code. Pinned in Task 5.
5. **The brain dies mid-meeting** — expected: "Snoop here, my brain's offline", and the Conductor restarts it once. Pinned in Task 4, Step 4.

---

### Task 1: Production extension

**Files:**
- Create: `extension/` (copy of `spikes/extension/` after Plan 0: `manifest.json`, `bridge_sw.js`, `content.js`, `caption_parse.js`, `page_media.js`, `package.json`, `test/`)
- Modify: `extension/content.js` (meeting code message; captions auto-on; caption observer)
- Create: `tests/test_extension_prod.py` (the Plan 0 manifest and no-input tests, pointed at `extension/`)
- Modify: `.gitignore` (`extension/config.local.json`, `extension/node_modules/`)

**Interfaces:**
- Produces messages page → Conductor: `{"type": "meeting", "code": "abc-defg-hij"}` once per page load; `{"type": "caption", "speaker": str, "text": str, "ts": float}`; `{"type": "health", "captions_seen_s_ago": float}` every 30 s. Conductor → page: `audio`, `stop`, `card` (unchanged from Plan 0).

- [ ] **Step 1: Copy and re-point tests** — copy the spike extension; copy `spikes/test_extension_manifest.py` to `tests/test_extension_prod.py` with `EXT = pathlib.Path("extension")`; change the manifest `name` to `"Snoop"` and `version` to `"0.1.0"`.

Run: `uv run pytest tests/test_extension_prod.py -q && (cd extension && npm install && npm test)`
Expected: all PASS (the spike's tests on the promoted copy).

- [ ] **Step 2: Failing test — meeting code extraction**

```js
// extension/test/meeting_code.test.mjs
import {test} from "node:test";
import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require = createRequire(import.meta.url);
const {meetingCodeFrom} = require("../caption_parse.js");

test("extracts the meeting code from a Meet path", () => {
  assert.equal(meetingCodeFrom("/abc-defg-hij"), "abc-defg-hij");
  assert.equal(meetingCodeFrom("/abc-defg-hij?authuser=1"), "abc-defg-hij");
  assert.equal(meetingCodeFrom("/landing"), null);
});
```

Run: `cd extension && npm test` → Expected: FAIL (`meetingCodeFrom is not a function`)

- [ ] **Step 3: Implement** — add to `extension/caption_parse.js`:

```js
function meetingCodeFrom(path) {
  const m = /^\/([a-z]{3}-[a-z]{4}-[a-z]{3})\b/.exec(path);
  return m ? m[1] : null;
}
if (typeof module !== "undefined") module.exports = {parseCaptions, meetingCodeFrom};
```

(replace the existing `module.exports` line). In `content.js`, after `chrome.runtime.connect`, send `{type: "meeting", code: meetingCodeFrom(location.pathname)}` when non-null; keep the Plan 0 `MutationObserver` that emits captions; add a 30-second `health` message with seconds since the last caption; add `function turnOnCaptions()` that clicks the captions button once if the caption region is absent (the only `.click()` the no-input test allows).

Run: `cd extension && npm test && cd .. && uv run pytest tests/test_extension_prod.py -q` → Expected: all PASS.

- [ ] **Step 4: Commit** — `git add extension tests/test_extension_prod.py .gitignore && git commit -m "extension: production copy with meeting code, health, captions auto-on"`

---

### Task 2: Conductor state machine (pure)

**Files:**
- Create: `yosnoop/conductor/__init__.py`, `yosnoop/conductor/state.py`, `yosnoop/wake.py` (promoted `spikes/p2_wake.py`), `yosnoop/seats.py` (promoted `spikes/p7_seats.py`), `tests/test_state.py`

**Interfaces:**
- Consumes: `yosnoop.roster.Roster`, `yosnoop.wake.is_wake/is_stop`, `yosnoop.seats.stand_down`
- Produces: actions (frozen dataclasses) `StopAudio()`, `Ask(asker: str, question: str)`, `StandDown(other: str)`; `Conductor(roster, host_email, own_label="You", silence_s=1.5)` with `on_caption(speaker, text, ts) -> list[Action]`, `on_tick(now) -> list[Action]`, properties `muted: bool`, `passive: bool`; `strip_wake(text) -> str`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_state.py
from yosnoop.conductor.state import Conductor, StopAudio, Ask, StandDown, strip_wake
from yosnoop.roster import load

R = load("config/team.json")
def c(host="brett@startup.ai"): return Conductor(R, host)

def test_wake_then_silence_asks_once():
    s = c()
    assert s.on_caption("Jeremy Leeds", "Yo Snoop, how many PRs merged", 10.0) == []
    assert s.on_caption("Jeremy Leeds", "Yo Snoop, how many PRs merged yesterday?", 10.8) == []
    assert s.on_tick(11.0) == []
    assert s.on_tick(12.4) == [Ask("Jeremy Leeds", "how many PRs merged yesterday?")]
    assert s.on_tick(13.0) == []

def test_own_seat_never_acts():
    s = c()
    assert s.on_caption("You", "Yo Snoop, peanut butter", 1.0) == []
    assert s.on_tick(5.0) == [] and not s.muted

def test_peanut_butter_mutes_until_wake():
    s = c()
    assert s.on_caption("Some Guest", "ok peanut butter", 1.0) == [StopAudio()]
    assert s.muted
    s.on_caption("Jeremy Leeds", "Yo Snoop, CI status?", 2.0)
    assert not s.muted

def test_decoys_do_not_trigger():
    s = c()
    s.on_caption("Jeremy Leeds", "we should snoop around the logs", 1.0)
    assert s.on_tick(5.0) == []

def test_lower_priority_snoop_stands_down_once():
    s = c("jeremy@startup.ai")
    assert s.on_caption("Brett Evans", "Snoop here, CI is green", 1.0) == [StandDown("Brett Evans")]
    assert s.passive
    assert s.on_caption("Brett Evans", "Snoop here, again", 2.0) == []
    s.on_caption("Lindsay Palmer", "Yo Snoop, anything?", 3.0)
    assert s.on_tick(9.0) == []

def test_higher_priority_snoop_stays():
    s = c("brett@startup.ai")
    assert s.on_caption("Jeremy Leeds", "Snoop here, CI is green", 1.0) == []
    assert not s.passive

def test_strip_wake():
    assert strip_wake("Yo, Snoopy, any blockers?") == "any blockers?"
```

Run: `uv run pytest tests/test_state.py -q` → Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 2: Implement**

```python
# yosnoop/conductor/state.py
import re
from dataclasses import dataclass
from yosnoop.wake import is_wake, is_stop
from yosnoop.seats import stand_down

_WAKE_PREFIX = re.compile(r"^\W*(yo|you|yoh|yeah)\W+snoop(y|s)?\b\W*", re.IGNORECASE)


@dataclass(frozen=True)
class StopAudio: pass

@dataclass(frozen=True)
class Ask:
    asker: str
    question: str

@dataclass(frozen=True)
class StandDown:
    other: str


def strip_wake(text: str) -> str:
    return _WAKE_PREFIX.sub("", text, count=1).strip()


class Conductor:
    def __init__(self, roster, host_email: str, own_label: str = "You", silence_s: float = 1.5):
        self.roster, self.host, self.own, self.silence = roster, host_email, own_label, silence_s
        self.muted = False
        self.passive = False
        self._pending = None  # (speaker, line, last_ts)

    def on_caption(self, speaker: str, text: str, ts: float) -> list:
        if speaker == self.own:
            return []
        if self.passive:
            return []
        if stand_down(self.host, speaker, text, self.roster):
            self.passive, self._pending = True, None
            return [StandDown(speaker)]
        if is_stop(text):
            self.muted, self._pending = True, None
            return [StopAudio()]
        if is_wake(text):
            self.muted = False
            self._pending = (speaker, text, ts)
            return []
        if self._pending and self._pending[0] == speaker:
            self._pending = (speaker, text if text.startswith(self._pending[1][:10]) else self._pending[1] + " " + text, ts)
        return []

    def on_tick(self, now: float) -> list:
        if self.passive or not self._pending:
            return []
        speaker, line, last = self._pending
        if now - last < self.silence:
            return []
        self._pending = None
        q = strip_wake(line)
        return [Ask(speaker, q)] if q else []
```

`yosnoop/wake.py` and `yosnoop/seats.py` are verbatim copies of `spikes/p2_wake.py` and `spikes/p7_seats.py` with imports changed to `yosnoop.roster`.

- [ ] **Step 3: Green** — `uv run pytest tests/test_state.py -q` → 7 PASS
- [ ] **Step 4: Commit** — `git add yosnoop/conductor yosnoop/wake.py yosnoop/seats.py tests/test_state.py && git commit -m "conductor: pure state machine (wake, mute, own seat, stand-down)"`

---

### Task 3: Room and asker checks (fail closed)

**Files:**
- Create: `yosnoop/room.py`, `tests/test_room.py`

**Interfaces:**
- Consumes: the classifier shape from `spikes/p1_meet_participants.py`
- Produces: `Participant(kind: str, user_id: str | None, display: str, email: str | None)`; `verdict(participants, roster, own_user_id) -> "team" | "mixed"`; `asker_allowed(speaker, participants, roster, room) -> bool`; `RoomWatcher(code, fetch, resolve_email, own_user_id, roster, ttl_s=5)` with `async current() -> tuple[str, list[Participant]]` that returns `("mixed", [])` on any fetch error.

- [ ] **Step 1: Failing tests**

```python
# tests/test_room.py
import asyncio
from yosnoop.room import Participant, verdict, asker_allowed, RoomWatcher
from yosnoop.roster import load

R = load("config/team.json")
B = Participant("signed_in", "users/1", "Brett Evans", "brett@startup.ai")
J = Participant("signed_in", "users/2", "Jeremy Leeds", "jeremy@startup.ai")
G = Participant("signed_in", "users/9", "Guest Person", "guest@gmail.com")
A = Participant("anonymous", None, "Jeremy Leeds", None)
P = Participant("phone", None, "+1 415", None)

def test_all_team_is_team():
    assert verdict([B, J], R, own_user_id="users/1") == "team"

def test_any_outsider_kind_is_mixed():
    for x in (G, A, P):
        assert verdict([B, J, x], R, own_user_id="users/1") == "mixed"

def test_asker_must_be_unique_verified_team_member():
    assert asker_allowed("Jeremy Leeds", [B, J], R, "team")
    assert not asker_allowed("Jeremy Leeds", [B, J, A], R, "team")  # duplicate name: anonymous impostor
    assert not asker_allowed("Guest Person", [B, G], R, "mixed")

def test_fetch_error_fails_closed():
    async def boom(code): raise RuntimeError("403")
    w = RoomWatcher("abc-defg-hij", boom, lambda uid: None, "users/1", R)
    assert asyncio.run(w.current()) == ("mixed", [])
```

Run: `uv run pytest tests/test_room.py -q` → Expected: FAIL

- [ ] **Step 2: Implement**

```python
# yosnoop/room.py
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Participant:
    kind: str
    user_id: str | None
    display: str
    email: str | None


def _is_team(p: Participant, roster) -> bool:
    return p.kind == "signed_in" and bool(p.email) and p.email.lower().endswith("@" + roster.domain)


def verdict(participants, roster, own_user_id: str) -> str:
    others = [p for p in participants if p.user_id != own_user_id]
    return "team" if all(_is_team(p, roster) for p in others) else "mixed"


def asker_allowed(speaker: str, participants, roster, room: str) -> bool:
    named = [p for p in participants if p.display == speaker]
    if len(named) != 1 or not _is_team(named[0], roster):
        return False
    if room == "mixed":
        m = roster.by_email(named[0].email)
        return bool(m and m.mixed_room_asker)
    return True


class RoomWatcher:
    def __init__(self, code, fetch, resolve_email, own_user_id, roster, ttl_s=5.0):
        self.code, self.fetch, self.resolve, self.own, self.roster, self.ttl = code, fetch, resolve_email, own_user_id, roster, ttl_s
        self._at, self._cache = 0.0, ("mixed", [])

    async def current(self, force: bool = False):
        if not force and time.monotonic() - self._at < self.ttl:
            return self._cache
        try:
            raw = await self.fetch(self.code)
            ps = [Participant(k, uid, name, self.resolve(uid) if uid else None) for k, uid, name in raw]
            self._cache = (verdict(ps, self.roster, self.own), ps)
        except Exception:
            self._cache = ("mixed", [])
        self._at = time.monotonic()
        return self._cache
```

The production adapter, built from `spikes/p1_meet_participants.py`:

```python
# yosnoop/google_meet.py
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from yosnoop.paths import secrets_dir

SCOPES = ["https://www.googleapis.com/auth/meetings.space.readonly",
          "https://www.googleapis.com/auth/directory.readonly"]


def classify(p: dict) -> tuple[str, str | None, str]:
    if "signedinUser" in p:
        u = p["signedinUser"]; return "signed_in", u.get("user"), u.get("displayName", "")
    if "phoneUser" in p:
        return "phone", None, p["phoneUser"].get("displayName", "")
    return "anonymous", None, p.get("anonymousUser", {}).get("displayName", "")


def google_login() -> None:
    """`./snoop google-login`: one browser sign-in by the host; stores a read-only token."""
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_dir() / "client_secret.json"), SCOPES)
    c = flow.run_local_server(port=0)
    tok = secrets_dir() / "meet-token.json"; tok.write_text(c.to_json()); tok.chmod(0o600)


class GoogleMeet:
    def __init__(self):
        tok = secrets_dir() / "meet-token.json"
        c = Credentials.from_authorized_user_file(str(tok), SCOPES)
        if c.expired and c.refresh_token:
            c.refresh(Request()); tok.write_text(c.to_json()); tok.chmod(0o600)
        self.meet = build("meet", "v2", credentials=c, cache_discovery=False)
        self.people = build("people", "v1", credentials=c, cache_discovery=False)
        self._emails: dict[str, str | None] = {}

    def own_user_id(self) -> str:
        me = self.people.people().get(resourceName="people/me", personFields="emailAddresses").execute()
        return "users/" + me["resourceName"].split("/", 1)[1]

    def _fetch(self, code: str):
        recs = self.meet.conferenceRecords().list(filter=f'space.meeting_code = "{code}" AND end_time IS NULL').execute()
        out = []
        for rec in recs.get("conferenceRecords", []):
            ps = self.meet.conferenceRecords().participants().list(parent=rec["name"]).execute()
            out += [classify(p) for p in ps.get("participants", []) if not p.get("latestEndTime")]
        return out

    async def fetch(self, code: str):
        return await asyncio.to_thread(self._fetch, code)

    def resolve_email(self, user_id: str) -> str | None:
        if user_id not in self._emails:
            try:
                r = self.people.people().get(resourceName="people/" + user_id.split("/", 1)[1],
                                             personFields="emailAddresses").execute()
                self._emails[user_id] = (r.get("emailAddresses") or [{}])[0].get("value")
            except Exception:
                self._emails[user_id] = None  # unresolvable → not team → mixed
        return self._emails[user_id]
```

`yosnoop/cli.py` gains `google-login` (calls `google_login()`); the runbook (Plan 3) has the host copy the Plan 0 `client_secret.json` to `~/.config/snoop/secrets/` first. `resolve_email` is synchronous and cached; the first lookups happen inside `fetch`'s thread on the next call, so call `resolve_email` from `asyncio.to_thread` in `RoomWatcher` callers if profiling shows a stall.

- [ ] **Step 3: Green** — 4 PASS. **Step 4: Commit** — `git add yosnoop/room.py yosnoop/google_meet.py yosnoop/cli.py tests/test_room.py && git commit -m "room: verdict and asker checks, fail closed"`

---

### Task 4: Brain client (starts Plan 1's brain; key on stdin)

**Files:**
- Create: `yosnoop/brain_client.py`, `tests/test_brain_client.py`

**Interfaces:**
- Consumes: Plan 1 protocol (`key`/`dev`/`ask`/`end_meeting` in; `answer`/`error` out); `paths.bin_dir()`
- Produces: `BrainClient(argv: list[str], first_line: dict)`; `async start()`, `async ask(question, asker, room) -> BrainReply(ok: bool, text: str, clone_age_s: float, reason: str | None)`, `async end_meeting()`, `async stop()`; restarts the process once if it exits, then reports `reason="offline"`. `production_argv() -> list[str]` = `["sudo", "-n", "-u", "snoop", str(bin_dir()/"brain")]`; `keychain_key() -> str` via `security find-generic-password -s snoop-anthropic -a $USER -w` (stdout captured, never logged).

- [ ] **Step 1: Failing tests with a fake brain**

```python
# tests/test_brain_client.py
import asyncio, sys, textwrap
from yosnoop.brain_client import BrainClient

FAKE = textwrap.dedent('''
import json, sys
cred = None
for line in sys.stdin:
    m = json.loads(line)
    if m["type"] in ("key", "dev"): cred = m["type"]; continue
    if m["type"] == "ask":
        if m["question"] == "die": sys.exit(1)
        print(json.dumps({"type": "answer", "id": m["id"], "text": f"{cred}:{m['question']}", "clone_age_s": 1.0}), flush=True)
''')

def client(tmp_path):
    f = tmp_path / "fake_brain.py"; f.write_text(FAKE)
    return BrainClient([sys.executable, str(f)], {"type": "dev"})

def test_ask_round_trip(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r = await c.ask("hello", "Brett Evans", "team"); await c.stop(); return r
    r = asyncio.run(go())
    assert r.ok and r.text == "dev:hello"

def test_dead_brain_restarts_once_then_reports_offline(tmp_path):
    async def go():
        c = client(tmp_path); await c.start()
        r1 = await c.ask("die", "x", "team")
        r2 = await c.ask("hello", "x", "team")
        await c.stop(); return r1, r2
    r1, r2 = asyncio.run(go())
    assert not r1.ok and r1.reason == "offline"
    assert r2.ok
```

Run → FAIL (`ModuleNotFoundError`).

- [ ] **Step 2: Implement**

```python
# yosnoop/brain_client.py
import asyncio, itertools, json, os, subprocess
from dataclasses import dataclass
from yosnoop import paths


@dataclass(frozen=True)
class BrainReply:
    ok: bool
    text: str
    clone_age_s: float
    reason: str | None


def production_argv() -> list[str]:
    return ["sudo", "-n", "-u", "snoop", str(paths.bin_dir() / "brain")]


def keychain_key() -> str:
    return subprocess.run(["security", "find-generic-password", "-s", "snoop-anthropic", "-a", os.environ["USER"], "-w"],
                          capture_output=True, text=True, check=True).stdout.strip()


class BrainClient:
    def __init__(self, argv, first_line: dict):
        self.argv, self.first, self.proc, self.ids = argv, first_line, None, itertools.count(1)

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(*self.argv, stdin=asyncio.subprocess.PIPE,
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        self.proc.stdin.write((json.dumps(self.first) + "\n").encode()); await self.proc.stdin.drain()

    async def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode()); await self.proc.stdin.drain()

    async def ask(self, question: str, asker: str, room: str, _retry=True) -> BrainReply:
        rid = str(next(self.ids))
        try:
            await self._send({"type": "ask", "id": rid, "question": question, "asker": asker, "room": room})
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=100)
            if not line:
                raise ConnectionError("brain exited")
            m = json.loads(line)
            if m["type"] == "answer":
                return BrainReply(True, m["text"], m.get("clone_age_s", float("inf")), None)
            return BrainReply(False, "", float("inf"), m.get("reason"))
        except (ConnectionError, BrokenPipeError, asyncio.TimeoutError):
            if _retry:
                await self.start()
            return BrainReply(False, "", float("inf"), "offline")

    async def end_meeting(self):
        await self._send({"type": "end_meeting"})

    async def stop(self):
        if self.proc and self.proc.returncode is None:
            self.proc.stdin.close()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError:
                self.proc.kill()
```

- [ ] **Step 3: Green** — 2 PASS.
- [ ] **Step 4: Commit** — `git add yosnoop/brain_client.py tests/test_brain_client.py && git commit -m "brain client: spawn, key on stdin, restart once"`

---

### Task 5: Speech shaping, TTS, Chat poster

**Files:**
- Create: `yosnoop/speech.py`, `yosnoop/chat.py`, `yosnoop/voice.py`, `tests/test_speech.py`, `tests/test_chat.py`

**Interfaces:**
- Produces:
  - `sentences(text) -> list[str]`; `shape(answer: str, clone_age_s: float) -> Shaped(spoken: list[str], chat_full: str | None)` — spoken = `["Snoop here.", <≤3 sentences>]` plus `"My notes are N minutes old."` when age > 1800 s; `chat_full` = whole answer when more than 3 sentences, else `None`.
  - `ChatPoster(space: str, post_fn)` with `post(text, mention_user_id=None)`; refuses (raises `ValueError`) any `space` argument other than its configured one.
  - `Voice` protocol `async say(sentence)`, `async stop()`; `ExtensionVoice(bridge_app, synth)` sends `audio` messages; `BlackholeVoice(synth)` plays via `sounddevice` (only if Plan 0 chose it); `synth(sentence) -> bytes` = Google TTS LINEAR16 24 kHz, header stripped, key `~/.config/snoop/secrets/tts-key.json`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_speech.py
from yosnoop.speech import sentences, shape

LONG = "One. Two is here. Three? Four! Five."

def test_sentences():
    assert sentences(LONG) == ["One.", "Two is here.", "Three?", "Four!", "Five."]

def test_short_answer_spoken_only():
    s = shape("CI is green. Three PRs merged.", 60)
    assert s.spoken == ["Snoop here.", "CI is green.", "Three PRs merged."] and s.chat_full is None

def test_long_answer_speaks_three_and_posts_all():
    s = shape(LONG, 60)
    assert s.spoken == ["Snoop here.", "One.", "Two is here.", "Three?"] and s.chat_full == LONG

def test_stale_notes_are_disclosed():
    assert shape("CI is green.", 3600).spoken[-1] == "My notes are 60 minutes old."
```

```python
# tests/test_chat.py
import pytest
from yosnoop.chat import ChatPoster

def test_posts_to_configured_space_with_mention():
    sent = []
    ChatPoster("spaces/AAA", lambda space, body: sent.append((space, body))).post("hi", "users/1")
    assert sent == [("spaces/AAA", {"text": "<users/1> hi"})]

def test_refuses_other_space():
    with pytest.raises(ValueError):
        ChatPoster("spaces/AAA", lambda s, b: None).post("hi", space="spaces/BBB")
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/speech.py
import re
from dataclasses import dataclass

_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Shaped:
    spoken: list[str]
    chat_full: str | None


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text.strip()) if s.strip()]


def shape(answer: str, clone_age_s: float) -> Shaped:
    ss = sentences(answer)
    spoken = ["Snoop here."] + ss[:3]
    if clone_age_s > 1800:
        spoken.append(f"My notes are {int(clone_age_s // 60)} minutes old.")
    return Shaped(spoken, answer if len(ss) > 3 else None)
```

```python
# yosnoop/chat.py
class ChatPoster:
    def __init__(self, space: str, post_fn):
        self.space, self.post_fn = space, post_fn

    def post(self, text: str, mention_user_id: str | None = None, space: str | None = None):
        if space is not None and space != self.space:
            raise ValueError(f"refusing to post outside the configured space: {space}")
        body = {"text": (f"<{mention_user_id}> " if mention_user_id else "") + text}
        self.post_fn(self.space, body)
```

The production `post_fn` (in `chat.py`):

```python
def google_post_fn():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from yosnoop.paths import secrets_dir
    creds = service_account.Credentials.from_service_account_file(
        str(secrets_dir() / "chat-key.json"), scopes=["https://www.googleapis.com/auth/chat.bot"])
    chat = build("chat", "v1", credentials=creds, cache_discovery=False)
    return lambda space, body: chat.spaces().messages().create(parent=space, body=body).execute()
```

```python
# yosnoop/voice.py
import asyncio, base64
from google.cloud import texttospeech
from yosnoop.bridge import broadcast
from yosnoop.paths import secrets_dir

RATE = 24000


class GoogleSynth:
    def __init__(self):
        self.c = texttospeech.TextToSpeechClient.from_service_account_file(str(secrets_dir() / "tts-key.json"))

    def __call__(self, text: str) -> bytes:
        r = self.c.synthesize_speech(input=texttospeech.SynthesisInput(text=text),
                                     voice=texttospeech.VoiceSelectionParams(language_code="en-US"),
                                     audio_config=texttospeech.AudioConfig(
                                         audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=RATE))
        return r.audio_content[44:]


class ExtensionVoice:
    def __init__(self, bridge_app, synth):
        self.app, self.synth = bridge_app, synth

    async def say(self, sentence: str):
        pcm = await asyncio.to_thread(self.synth, sentence)
        await broadcast(self.app, {"type": "audio", "pcm_b64": base64.b64encode(pcm).decode(), "rate": RATE})
        await asyncio.sleep(len(pcm) / (RATE * 2))  # wait out playback so the next room re-check is current

    async def stop(self):
        await broadcast(self.app, {"type": "stop"})


class BlackholeVoice:  # only if Plan 0 Task 7 chose BlackHole
    def __init__(self, synth):
        self.synth = synth

    async def say(self, sentence: str):
        import numpy as np, sounddevice as sd
        pcm = await asyncio.to_thread(self.synth, sentence)
        sd.play(np.frombuffer(pcm, dtype="<i2"), RATE, device="BlackHole 2ch")
        await asyncio.to_thread(sd.wait)

    async def stop(self):
        import sounddevice as sd
        sd.stop()
```

`yosnoop/bridge.py` is `spikes/bridge_server.py` promoted verbatim (with `CLIENTS` and `broadcast`).

- [ ] **Step 3: Green** — 6 PASS. **Step 4: Commit** — `git add yosnoop/speech.py yosnoop/chat.py yosnoop/voice.py yosnoop/bridge.py tests/test_speech.py tests/test_chat.py && git commit -m "speech shaping (Snoop here, 3 sentences, stale notes), Chat poster, voice"`

---

### Task 6: Delivery — gate, per-sentence room re-check, Chat fallback

**Files:**
- Create: `yosnoop/conductor/deliver.py`, `tests/test_deliver.py`

**Interfaces:**
- Consumes: `gate.gate`, `speech.shape`, `RoomWatcher.current(force=True)`, `Voice`, `ChatPoster`
- Produces: `async deliver(answer: BrainReply, asker_user_id, room_at_ask, watcher, voice, chat, muted: Callable[[], bool]) -> str` returning `"spoken"`, `"chat"`, `"partial-then-chat"`, `"blocked"` or `"offline"`.

- [ ] **Step 1: Failing tests** (fakes for voice, chat, watcher)

```python
# tests/test_deliver.py
import asyncio
from yosnoop.brain_client import BrainReply
from yosnoop.conductor.deliver import deliver

class V:
    def __init__(self): self.said = []
    async def say(self, s): self.said.append(s)
    async def stop(self): self.said.append("<stop>")

class C:
    def __init__(self): self.posts = []
    def post(self, text, mention_user_id=None, space=None): self.posts.append(text)

class W:
    def __init__(self, seq): self.seq = list(seq)
    async def current(self, force=False): return (self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]), []

def run(reply, room, seq, muted=lambda: False):
    v, c = V(), C()
    r = asyncio.run(deliver(reply, "users/2", room, W(seq), v, c, muted))
    return r, v.said, c.posts

def test_team_room_speaks():
    r, said, posts = run(BrainReply(True, "CI is green.", 60, None), "team", ["team"])
    assert r == "spoken" and said == ["Snoop here.", "CI is green."] and posts == []

def test_mixed_room_posts_and_only_says_sent():
    r, said, posts = run(BrainReply(True, "CI is green.", 60, None), "mixed", ["mixed"])
    assert r == "chat" and said == ["Snoop here, sent it to Chat."] and posts == ["CI is green."]

def test_outsider_joins_mid_answer():
    r, said, posts = run(BrainReply(True, "One. Two. Three.", 60, None), "team", ["team", "team", "mixed"])
    assert r == "partial-then-chat" and said[-1] == "<stop>" and posts == ["One. Two. Three."]

def test_secret_is_blocked():
    r, said, posts = run(BrainReply(True, "key " + "ghp_" + "Q" * 36, 60, None), "team", ["team"])
    assert r == "blocked" and said == ["Snoop here, can't share that one."] and posts == []

def test_offline_brain():
    r, said, _ = run(BrainReply(False, "", 0, "offline"), "team", ["team"])
    assert r == "offline" and said == ["Snoop here, my brain's offline."]

def test_muted_mid_answer_stops_speech_and_posts_rest():
    flags = iter([False, True, True, True])
    r, said, posts = run(BrainReply(True, "One. Two. Three.", 60, None), "team", ["team"], muted=lambda: next(flags))
    assert said[-1] == "<stop>" and posts == ["One. Two. Three."]
```

Run → FAIL.

- [ ] **Step 2: Implement**

```python
# yosnoop/conductor/deliver.py
from yosnoop.gate import gate
from yosnoop.speech import shape


async def deliver(reply, asker_user_id, room_at_ask, watcher, voice, chat, muted) -> str:
    if not reply.ok:
        await voice.say("Snoop here, my brain's offline." if reply.reason == "offline" else "Snoop here, lost the thread, ask again.")
        return "offline"
    g = gate(reply.text)
    if not g.allowed:
        await voice.say(g.text)
        return "blocked"
    if room_at_ask != "team":
        chat.post(g.text, asker_user_id)
        await voice.say("Snoop here, sent it to Chat.")
        return "chat"
    shaped = shape(g.text, reply.clone_age_s)
    for i, s in enumerate(shaped.spoken):
        room, _ = await watcher.current(force=True)
        if room != "team" or muted():
            await voice.stop()
            chat.post(g.text, asker_user_id)
            return "partial-then-chat"
        await voice.say(s)
    if shaped.chat_full:
        chat.post(shaped.chat_full, asker_user_id)
    return "spoken"
```

- [ ] **Step 3: Green** — 6 PASS. **Step 4: Commit** — `git add yosnoop/conductor/deliver.py tests/test_deliver.py && git commit -m "delivery: gate, per-sentence room re-check, Chat fallback"`

---

### Task 7: Conductor runtime and `./snoop start`

**Files:**
- Create: `yosnoop/conductor/run.py`, `yosnoop/qlog.py`, `tests/test_qlog.py`, `tests/test_run_wiring.py`
- Modify: `yosnoop/start.py` (meeting half), `yosnoop/cli.py` (`start [--dev]`)

**Interfaces:**
- Consumes: everything above; `bridge_server.make_app` (promoted to `yosnoop/bridge.py` from `spikes/bridge_server.py`); Plan 1 `prepare()`.
- Produces: `run_meeting_loop(cfg) -> None` — starts bridge on 127.0.0.1:8790, waits for `meeting` message, builds `RoomWatcher`, ticks `Conductor` every 200 ms, executes actions (`StopAudio` → `voice.stop()`; `Ask` → asker check → brain → `deliver`; `StandDown` → one Chat post "Snoop (<me>) is standing down; Snoop (<other>) has this meeting."), refreshes knowledge every 5 min, posts "Snoop dropped" to Chat on bridge disconnect > 60 s, and on a `health` message with `captions_seen_s_ago > 60` posts a one-time Chat warning. `qlog.write(entry)` / `qlog.prune(days=7)`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_qlog.py
import datetime, json, pytest
from yosnoop import qlog

E = {"ts": 1.0, "asker": "Jeremy Leeds", "room": "team", "question": "CI?", "outcome": "spoken", "latency_s": 2.1}

def test_write_has_exact_fields(tmp_path):
    qlog.write(E, tmp_path, today=datetime.date(2026, 10, 6))
    line = json.loads((tmp_path / "questions-2026-10-06.ndjson").read_text())
    assert set(line) == set(qlog.FIELDS)

def test_write_rejects_extra_fields(tmp_path):
    with pytest.raises(ValueError):
        qlog.write({**E, "caption": "anything"}, tmp_path)

def test_prune_keeps_seven_days(tmp_path):
    for d in ("2026-09-28", "2026-09-30", "2026-10-06"):
        (tmp_path / f"questions-{d}.ndjson").write_text("{}")
    qlog.prune(tmp_path, days=7, today=datetime.date(2026, 10, 6))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["questions-2026-09-30.ndjson", "questions-2026-10-06.ndjson"]
```

```python
# tests/test_run_wiring.py
import asyncio
from yosnoop.brain_client import BrainReply
from yosnoop.conductor.run import Ctx, handle_event, tick
from yosnoop.conductor.state import Conductor
from yosnoop.room import Participant
from yosnoop.roster import load

R = load("config/team.json")
B = Participant("signed_in", "users/1", "Brett Evans", "brett@startup.ai")
J = Participant("signed_in", "users/2", "Jeremy Leeds", "jeremy@startup.ai")
IMP = Participant("anonymous", None, "Jeremy Leeds", None)

class W:
    def __init__(self, ps): self.ps = ps
    async def current(self, force=False): return ("team" if all(p.kind == "signed_in" for p in self.ps) else "mixed"), self.ps

class Brain:
    async def ask(self, q, asker, room): return BrainReply(True, "CI is green.", 60, None)

class V:
    def __init__(self): self.said = []
    async def say(self, s): self.said.append(s)
    async def stop(self): self.said.append("<stop>")

class C:
    def __init__(self): self.posts = []
    def post(self, text, mention_user_id=None, space=None): self.posts.append(text)

def run(participants):
    v, c, logs = V(), C(), []
    ctx = Ctx(conductor=Conductor(R, "brett@startup.ai"), roster=R, brain=Brain(), voice=v, chat=c,
              make_watcher=lambda code: W(participants), log=logs.append)
    async def go():
        await handle_event(ctx, {"type": "meeting", "code": "abc-defg-hij"})
        await handle_event(ctx, {"type": "caption", "speaker": "Jeremy Leeds", "text": "Yo Snoop, CI?", "ts": 1.0})
        await tick(ctx, 3.0)
        await asyncio.gather(*ctx.tasks)
    asyncio.run(go())
    return v.said, c.posts, logs

def test_verified_teammate_gets_a_spoken_answer():
    said, posts, logs = run([B, J])
    assert said == ["Snoop here.", "CI is green."] and posts == []
    assert logs[0]["question"] == "CI?" and logs[0]["outcome"] == "spoken"

def test_impostor_name_is_refused():
    said, posts, logs = run([B, J, IMP])
    assert said == [] and posts == [] and logs[0]["outcome"] == "asker-refused"
```

Run: `uv run pytest tests/test_qlog.py tests/test_run_wiring.py -q` → Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 2: Implement**

```python
# yosnoop/qlog.py
import datetime, json
from pathlib import Path

FIELDS = ("ts", "asker", "room", "question", "outcome", "latency_s")


def write(entry: dict, logdir: Path, today: datetime.date | None = None) -> None:
    if set(entry) != set(FIELDS):
        raise ValueError(f"question log entries carry exactly {FIELDS}")
    day = (today or datetime.date.today()).isoformat()
    logdir.mkdir(parents=True, exist_ok=True)
    with open(logdir / f"questions-{day}.ndjson", "a") as f:
        f.write(json.dumps(entry) + "\n")


def prune(logdir: Path, days: int = 7, today: datetime.date | None = None) -> None:
    cutoff = (today or datetime.date.today()) - datetime.timedelta(days=days)
    for p in logdir.glob("questions-*.ndjson"):
        if datetime.date.fromisoformat(p.stem.removeprefix("questions-")) < cutoff:
            p.unlink()
```

```python
# yosnoop/conductor/run.py
import asyncio, time
from dataclasses import dataclass, field
from typing import Callable
from yosnoop.conductor.deliver import deliver
from yosnoop.conductor.state import Ask, StandDown, StopAudio
from yosnoop.room import asker_allowed


@dataclass
class Ctx:
    conductor: object
    roster: object
    brain: object
    voice: object
    chat: object
    make_watcher: Callable
    log: Callable[[dict], None]
    watcher: object = None
    tasks: set = field(default_factory=set)


async def handle_event(ctx: Ctx, m: dict) -> None:
    if m.get("type") == "meeting" and m.get("code"):
        ctx.watcher = ctx.make_watcher(m["code"])
    elif m.get("type") == "caption":
        await run_actions(ctx, ctx.conductor.on_caption(m["speaker"], m["text"], m["ts"]))


async def tick(ctx: Ctx, now: float) -> None:
    await run_actions(ctx, ctx.conductor.on_tick(now))


async def run_actions(ctx: Ctx, actions) -> None:
    for a in actions:
        if isinstance(a, StopAudio):
            await ctx.voice.stop()
        elif isinstance(a, StandDown):
            ctx.chat.post(f"Snoop is standing down in this meeting; Snoop ({a.other}) has it.")
        elif isinstance(a, Ask):
            t = asyncio.create_task(answer(ctx, a)); ctx.tasks.add(t); t.add_done_callback(ctx.tasks.discard)


async def answer(ctx: Ctx, a: Ask) -> None:
    t0 = time.monotonic()
    room, ps = await ctx.watcher.current(force=True) if ctx.watcher else ("mixed", [])
    entry = {"ts": time.time(), "asker": a.asker, "room": room, "question": a.question}
    if not asker_allowed(a.asker, ps, ctx.roster, room):
        ctx.log({**entry, "outcome": "asker-refused", "latency_s": 0.0}); return
    asker = next(p for p in ps if p.display == a.asker)
    reply = await ctx.brain.ask(a.question, a.asker, room)
    outcome = await deliver(reply, asker.user_id, room, ctx.watcher, ctx.voice, ctx.chat, lambda: ctx.conductor.muted)
    ctx.log({**entry, "outcome": outcome, "latency_s": round(time.monotonic() - t0, 2)})
```

`yosnoop/start.py` `run_start(argv)` wires the real pieces: `prepare()` (Plan 1); `qlog.prune`; promoted `make_ext_config` writes `extension/config.local.json`; `GoogleMeet()`; `own = meet.own_user_id()`; `Ctx(conductor=Conductor(roster, host.email, own_label=<Plan 0 OWN_LABEL>), make_watcher=lambda code: RoomWatcher(code, meet.fetch, meet.resolve_email, own, roster), brain=BrainClient(production_argv(), {"type": "key", "value": keychain_key()}) or, with `--dev`, BrainClient([sys.executable, "-m", "yosnoop.brain_main"], {"type": "dev"}) with a printed warning, voice=ExtensionVoice(bridge_app, GoogleSynth()) (or `BlackholeVoice`), chat=ChatPoster(<chat.json space>, google_post_fn()), log=lambda e: qlog.write(e, logdir))`; the bridge's `on_message` schedules `handle_event`; a 200 ms loop calls `tick(ctx, time.time())`; a 5-minute loop calls the Plan 1 refresher; a bridge-silence watchdog posts "Snoop dropped" after 60 s; a `health` message with `captions_seen_s_ago > 60` posts one Chat warning. It prints: "Open your Snoop Chrome profile, join the meeting, turn captions on."

- [ ] **Step 3: Green** — `uv run pytest -q` → all pass.
- [ ] **Step 4: Live smoke (Brett alone)** — `./snoop start --dev`, join a test meeting in the Snoop profile, say "Yo Snoop, how many open pull requests are there?" from a second device as Jeremy or Lindsay. Expected: card visible, "Snoop here." then the answer spoken; one entry in today's question log; no caption text in the log (`grep -c` for a sentence spoken earlier in the meeting → 0).
- [ ] **Step 5: Commit and push**

```bash
git add yosnoop extension tests
git commit -m "conductor runtime and ./snoop start"
git push
```
