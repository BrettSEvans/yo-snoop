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
