# Snoop Runbook — Desk Snoop

Desk Snoop listens on your Mac's microphone. Say "Yo Snoop, …" and it answers through your speakers, using a sandboxed, read-only copy of the Agent-C repo. Internal to Saasless only.

> **It answers out loud.** Run it only when everyone who can hear it is on the Saasless team.

---

## 1. What you need

- A Mac you are an admin on (you type your admin password once, in step 3).
- `uv`:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Node.js (any install; `node -v` works).
- `gh` signed in to an account that can read `Saasless-llc/Agent-C` and `brett-saasless/yo-snoop`:
  ```bash
  gh auth status
  ```
- Your saasless.ai email in `config/team.json` (ask Brett).
- About 4 GB free disk: the brain's runtime (~0.8 GB), the knowledge copy (~0.4 GB), the speech-recognition model (~0.5 GB), and Snoop's voice (~0.3 GB model plus its libraries).

## 2. Get the code

```bash
git clone https://github.com/brett-saasless/yo-snoop.git
cd yo-snoop
```

## 3. One-time setup

```bash
./snoop setup
```

1. Type your saasless.ai email.
2. It prints the whole script it will run. Read it, then type `yes`.
3. Type your Mac admin password when macOS asks (nothing shows while you type).
4. It ends with `snoop setup: done`.

What it changes: creates a hidden `snoop` user (no admin, no shell, its own group), the `/Users/Shared/snoop` folders, sets your home folder to `700` (other local accounts can't see in), and adds one sudo rule that lets you start only Snoop's brain as `snoop`.

Then build Snoop's notes and check the sandbox:

```bash
./snoop prepare
./snoop doctor
```

Then download Snoop's voice (Kokoro "Onyx", ~330 MB, runs on your Mac; nothing is sent anywhere when it speaks):

```bash
./snoop voice-setup
```

Without it Snoop still works, using the Mac's built-in voice.

`prepare` takes about 30 seconds after the first time. Every `doctor` line must say **PASS** once your key is in (step 4). If any line says FAIL, stop and send the output to Brett.

## 4. Your Snoop API key

Snoop uses an Anthropic API key from the Saasless Console organization linked to your Max or Team plan, so it draws on your plan's monthly API credits.

1. Link your plan to the Saasless Console organization: claude.ai → Settings → Billing → API credits. (Team owners do this once for the team.)
2. In the Console (console.anthropic.com), open the `Snoop` workspace → API Keys → Create Key, named after you. The key starts with `sk-ant-`.
3. Store it in your Keychain. Never paste it into chat, a doc, or a command line:
   ```bash
   security -i
   ```
   At the `security>` prompt, type the whole line below, with your key at the end in place of `PASTE-KEY-HERE`, then press Enter:
   ```
   add-generic-password -U -s snoop-anthropic -a YOUR-MAC-USERNAME -w PASTE-KEY-HERE
   ```
   Type that line **only at the `security>` prompt**. At the normal `%` prompt, zsh says "command not found" and saves the key in your shell history. Then press **Ctrl+D** to exit (`quit` doesn't work on current macOS). (`whoami` prints your Mac username.) Press **Cmd+K** to clear the Terminal window afterward.
   Use the macOS Terminal app for this, not a terminal inside another app that can read the screen.
4. Run `./snoop doctor` again. Every line must say PASS.

## 5. Microphone

The first `./snoop desk` makes macOS ask for microphone access for your terminal app. Click **Allow**. If you missed it: System Settings → Privacy & Security → Microphone → turn on your terminal app, then restart the terminal.

## 6. Use it

```bash
./snoop desk
```

- Say **"Yo Snoop,"** then your question, e.g. "Yo Snoop, how many open pull requests are there?"
- It says "Snoop here." and up to three sentences, and prints the full answer in the terminal.
- Say **"peanut butter"** to stop it talking. It stays quiet until the next "Yo Snoop".
- **Ctrl-C** quits.
- If its notes are more than 30 minutes old, it says so. Notes refresh at start and every 5 minutes.

Only questions that start with "Yo Snoop" are sent to the brain or logged. Audio never leaves your Mac and is never saved. The question log is at `~/.config/snoop/logs/` (question, who, when, outcome; kept 7 days).

Useful variants:

```bash
./snoop desk --dry
```
Listens and prints what it would do (WAKE / STOP), without asking the brain. Good for checking the mic.

```bash
./snoop desk --dev
```
Development only: the brain runs as you on your Claude login instead of as `snoop` with the Snoop key.

## 7. Update

```bash
git pull
```

The next `./snoop desk` re-syncs the brain.

## 8. If something's wrong

| You see / hear | Do this |
|---|---|
| "Snoop here, my brain's offline." | It restarts the brain once automatically. If it keeps happening, run `./snoop doctor` and send Brett the output. |
| "Snoop here, can't share that one." | The answer looked like it contained a secret, so it was blocked. Expected; rephrase or look it up yourself. |
| "No Snoop API key in your Keychain" | Do step 4. |
| "Peanut butter" doesn't stop it | Say it clearly, closer to the mic than the speakers are, and keep speaker volume moderate. Headphones avoid the problem entirely. |
| It never wakes | Run `./snoop desk --dry` and say "Yo Snoop, test". No `WAKE` line → check the microphone permission (step 5) and speak closer. |
| Credits ran out | Answers fail until the plan's monthly credits reset or the workspace limit is raised (owner decision). |
| Any `doctor` FAIL | Stop using Snoop and send Brett the full `./snoop doctor` output. |
