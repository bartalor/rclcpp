#!/usr/bin/env python3
"""Print one enabled plugin name per line, in the order they appear in
compose.yaml's include: list. Source of truth for what is "on" —
matches plugins/<name>/compose.yaml entries."""
import pathlib
import yaml

data = yaml.safe_load((pathlib.Path(__file__).parent / "compose.yaml").read_text())
for entry in data.get("include", []) or []:
    path = entry if isinstance(entry, str) else entry.get("path", "")
    if path.startswith("plugins/") and path.endswith(("/compose.yaml", "/compose.yml")):
        print(path.split("/")[1])
