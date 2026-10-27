from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

KEEP = frozenset({
    "read_file", "list_dir", "find_file", "search_for_pattern", "get_symbols_overview", "find_symbol",
    "find_referencing_symbols", "find_implementations", "find_declaration", "get_diagnostics_for_file",
    "get_diagnostics_for_symbol", "read_memory", "list_memories"})
REMOVED = frozenset({
    "create_text_file", "replace_content", "replace_in_files", "delete_lines", "replace_lines", "insert_at_line",
    "replace_symbol_body", "insert_after_symbol", "insert_before_symbol", "rename_symbol",
    "write_memory", "delete_memory", "rename_memory", "edit_memory", "onboarding",
    "execute_shell_command", "serena_repl", "open_dashboard", "activate_project", "remove_project",
    "query_project", "list_queryable_projects", "restart_language_server",
    "initial_instructions", "serena_info", "get_current_config", "safe_delete_symbol"})
ALL_KNOWN = KEEP | REMOVED


# Only the `ide` context honors read_only/fixed_tools (2.0.0: `agent` exposes editing and shell tools).
START_ARGS = ["start-mcp-server", "--context", "ide", "--agent-interface", "tools",
              "--enable-web-dashboard", "False", "--open-web-dashboard", "False", "--enable-gui-log-window", "False"]


def project_yml(name: str) -> str:
    """Allowlist (fixed_tools) plus read_only. Serena autofills the rest on a first, host-side run."""
    fixed = "\n".join(f"  - {t}" for t in sorted(KEEP))
    return (f'project_name: "{name}"\nlanguage_servers: ["typescript"]\nread_only: true\n'
            f"agent_interface: tools\nfixed_tools:\n{fixed}\n")


def assert_tools(exposed: set[str]) -> None:
    extra = sorted(exposed - KEEP)
    if extra:
        raise RuntimeError(f"Serena exposes tools outside the keep list: {extra}")


async def list_tools(command: list[str], errlog=None) -> set[str]:
    """errlog: where the server's own logging goes (default: this process's stderr)."""
    params = StdioServerParameters(command=command[0], args=command[1:])
    async with stdio_client(params, **({"errlog": errlog} if errlog else {})) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return {t.name for t in (await s.list_tools()).tools}
