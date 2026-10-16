import json
from pathlib import Path
from claude_agent_sdk import ClaudeAgentOptions
from yosnoop.serena_cfg import KEEP

KEY_STRIP = ["/usr/bin/env", "-u", "ANTHROPIC_API_KEY"]
# Allowlist of built-in tools; without it the CLI also exposes harness tools (RemoteTrigger, CronCreate, SendMessage...)
BASE_TOOLS = ["Read", "Grep", "Glob"]
DISALLOWED = ["Bash", "WebFetch", "WebSearch", "Write", "Edit", "NotebookEdit", "Task"]
REGISTRY_READ_TOOLS = ["registry_list", "registry_get", "stage_get", "stage_diagnose", "backlog_list",
                       "backlog_get", "history_events", "history_metrics", "server_info"]
SETTINGS = json.dumps({"permissions": {"blockReadsOutsideWorkingDirectories": True}})
SYSTEM = """You are Snoop, answering a Saasless team's questions about the Agent-C repo.
Answer only from files in your working directory and your tools. If you cannot find it, say "not in my notes".
git-facts.txt has branches and recent commits; pr-ci-status.json has pull requests and CI; repo-map.xml summarizes the code.
Lead with the answer. Plain sentences, no markdown; say identifiers exactly. Never claim CI passed unless a run says so.
Return the answer as short self-contained points, most important first. Never say the words "peanut butter"."""


def _server(cmd: list[str], env: dict | None = None) -> dict:
    s = {"type": "stdio", "command": KEY_STRIP[0], "args": [*KEY_STRIP[1:], *cmd]}
    if env:
        s["env"] = env
    return s


def build_options(knowledge: Path, registry_cmd, serena_cmd, model: str, persona: str = "", api_key: str | None = None):
    allowed, servers = [], {}
    if registry_cmd:
        servers["registry"] = _server(registry_cmd, {"AGENT_C_HOME": str(knowledge / "agent-c-home"),
                                                     "CLAUDE_PROJECTS_DIR": str(knowledge / "empty-projects")})
        allowed += [f"mcp__registry__{t}" for t in REGISTRY_READ_TOOLS]
    if serena_cmd:
        servers["serena"] = _server(serena_cmd)
        allowed += [f"mcp__serena__{t}" for t in sorted(KEEP)]
    return ClaudeAgentOptions(
        tools=list(BASE_TOOLS), allowed_tools=allowed, disallowed_tools=DISALLOWED, mcp_servers=servers,
        strict_mcp_config=True, setting_sources=[], settings=SETTINGS, permission_mode="dontAsk", max_turns=15,
        cwd=str(knowledge), model=model, env={"ANTHROPIC_API_KEY": api_key} if api_key else {},
        system_prompt=(persona + "\n\n" + SYSTEM).strip())
