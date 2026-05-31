#!/usr/bin/env python3
"""Register the memory MCP server in ~/.claude.json (idempotent).
The memory-server binary and its uv-managed venv are bind-mounted from the
host at the same /home/bar/.local/... path the venv's shebang expects."""
import json, pathlib

p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() else {}
servers = data.setdefault("mcpServers", {})
desired = {
    "type": "stdio",
    "command": "/home/bar/.local/bin/memory-server",
    "args": [],
    "env": {},
}
if servers.get("memory") != desired:
    servers["memory"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered memory MCP server in ~/.claude.json")
