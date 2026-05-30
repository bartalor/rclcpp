#!/usr/bin/env python3
"""Register the storybloq MCP server in ~/.claude.json (idempotent).

storybloq itself is provided via the bind-mounted ~/.npm-global from the host.
"""
import json
import pathlib

p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() else {}
servers = data.setdefault("mcpServers", {})
desired = {
    "type": "stdio",
    "command": str(pathlib.Path.home() / ".npm-global/bin/storybloq"),
    "args": ["--mcp"],
    "env": {"PATH": str(pathlib.Path.home() / ".nvm/versions/node/v20.20.2/bin")},
}
if servers.get("storybloq") != desired:
    servers["storybloq"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered storybloq MCP server in ~/.claude.json")
