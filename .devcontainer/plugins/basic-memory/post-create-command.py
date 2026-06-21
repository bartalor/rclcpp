#!/usr/bin/env python3
"""Install basic-memory (via uv) and register its MCP server in ~/.claude.json.

uv lives in the image at /usr/local/bin/uv (see Dockerfile). The host's
~/.local/bin is bind-mounted read-only, so we install into a container-owned
prefix under ~/.local/share/uv-tools and put the binary on PATH from there.
Both steps are idempotent."""
import json, os, pathlib, subprocess

VERSION = "0.21.5"  # pin to match host install
PREFIX = pathlib.Path.home() / ".local" / "share" / "uv-tools"
BIN = PREFIX / "bin" / "basic-memory"

env = {**os.environ, "UV_TOOL_DIR": str(PREFIX), "UV_TOOL_BIN_DIR": str(PREFIX / "bin")}
subprocess.run(
    ["/usr/local/bin/uv", "tool", "install", "--quiet", f"basic-memory=={VERSION}"],
    env=env, check=True,
)

p = pathlib.Path.home() / ".claude.json"
data = json.loads(p.read_text()) if p.exists() else {}
servers = data.setdefault("mcpServers", {})
desired = {
    "type": "stdio",
    "command": str(BIN),
    "args": ["mcp"],
    # Container user is "ubuntu", so Path.home() resolves to /home/ubuntu.
    # Point at the bind-mounted host data dirs under /home/bar.
    "env": {
        "BASIC_MEMORY_CONFIG_DIR": "/home/bar/.basic-memory",
        "BASIC_MEMORY_HOME": "/home/bar/basic-memory",
    },
}
if servers.get("basic-memory") != desired:
    servers["basic-memory"] = desired
    p.write_text(json.dumps(data, indent=2))
    print("registered basic-memory MCP server in ~/.claude.json")
