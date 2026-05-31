#!/usr/bin/env python3
"""Print one enabled plugin name per line, in the order they appear in
compose.yaml's include: list. Source of truth for what is "on" —
matches plugins/<name>/compose.yaml entries."""
import pathlib, re

text = (pathlib.Path(__file__).parent / "compose.yaml").read_text()
in_include = False
for line in text.splitlines():
    stripped = line.strip()
    if not in_include:
        if re.match(r"include\s*:\s*$", stripped):
            in_include = True
        continue
    # leave the include block when we hit a top-level key (no leading space)
    if line and not line[0].isspace() and not stripped.startswith("#"):
        break
    m = re.match(r"-\s*plugins/([^/]+)/compose\.ya?ml\s*$", stripped)
    if m:
        print(m.group(1))
