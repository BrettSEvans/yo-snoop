"""Test-only MCP server for doctor control C5: reports whether ANTHROPIC_API_KEY reached it. Never reports the value."""
import os
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("envprobe")


@mcp.tool()
def env_probe() -> str:
    """Report whether ANTHROPIC_API_KEY is set in this process."""
    return "present" if os.environ.get("ANTHROPIC_API_KEY") else "absent"


if __name__ == "__main__":
    mcp.run()
