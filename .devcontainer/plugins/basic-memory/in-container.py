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
    "env": {},
}
if servers.get("basic-memory") != desired:
    servers["basic-memory"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered basic-memory MCP server in ~/.claude.json")
