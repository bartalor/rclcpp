#!/usr/bin/env python3
"""Register the cpp (mcp-cpp-server) MCP server in ~/.claude.json (idempotent).
The binary is bind-mounted from the host's ~/.cargo/bin to /usr/local/bin."""
import json, pathlib

p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() else {}
servers = data.setdefault("mcpServers", {})
desired = {
    "type": "stdio",
    "command": "/usr/local/bin/mcp-cpp-server",
    "args": ["--root", "/opt/overlay_ws"],
    "env": {
        "CLANGD_PATH": "/usr/bin/clangd",
    },
}
if servers.get("cpp") != desired:
    servers["cpp"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered cpp MCP server in ~/.claude.json")
