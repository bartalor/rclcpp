#!/usr/bin/env python3
"""Register the basic-memory MCP server in ~/.claude.json (idempotent).
The basic-memory binary and its uv-managed venv are bind-mounted from the
host at the same /home/bar/.local/... path the venv's shebang expects."""
import json, pathlib

p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() else {}
servers = data.setdefault("mcpServers", {})
desired = {
    "type": "stdio",
    "command": "/home/bar/.local/bin/basic-memory",
    "args": ["mcp"],
    # Container user is "ubuntu", so Path.home() resolves to /home/ubuntu.
    # Override so basic-memory uses the bind-mounted host paths under /home/bar.
    "env": {
        "BASIC_MEMORY_CONFIG_DIR": "/home/bar/.basic-memory",
        "BASIC_MEMORY_HOME": "/home/bar/basic-memory",
    },
}
if servers.get("basic-memory") != desired:
    servers["basic-memory"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered basic-memory MCP server in ~/.claude.json")
