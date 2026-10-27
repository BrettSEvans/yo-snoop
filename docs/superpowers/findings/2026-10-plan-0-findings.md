# Plan 0 findings

Spec: docs/superpowers/specs/2026-10-05-yo-snoop-design.md · Plan: docs/superpowers/plans/2026-10-05-plan-0-verification-spikes.md

| Probe | Spec ref | Verdict | Evidence below | Consequence for Plans 1–2 |
|---|---|---|---|---|
| P1 Meet participants principal + latency | §8.1, §4 step 4 | | | |
| P2 Caption reading in the extension + wake accuracy | §8.2, §4 step 3 | | | |
| P3 Claude Code headless controls | §8.3, §5.3 | **PARTIAL** — Steps 1–5 HOLD; Step 6 (key helper) deferred to Plan 1 (D25) | §P3 | Plan 1 uses the SDK with `setting_sources=[]`, `strict_mcp_config`, `dontAsk`; `--max-turns` is SDK-only |
| P4 Voice + card via extension (BlackHole fallback) | §8.4, D28, D29 | | | |
| P5 Chat app, team group, one space | §8.5, §3.3 | | | |
| P6 Own-voice label | §8.6, D30 | | | |
| P7 Two-Snoop detection | §8.7, D32 | | | |

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
