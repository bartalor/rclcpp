#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "windows-repro.local.json"
REPO = "bartalor/rclcpp"
WORKFLOW = "windows-repro.yml"

if not CONFIG.exists():
    sys.exit(f"missing config: {CONFIG}")

config = json.loads(CONFIG.read_text())

rmws = config["rmws"]
if not isinstance(rmws, list) or not all(isinstance(r, str) for r in rmws):
    sys.exit('"rmws" must be a list of strings')

matrix = json.dumps({"rmw": rmws})
args = ["gh", "workflow", "run", WORKFLOW, "-R", REPO, "-f", f"matrix={matrix}"]
print(" ".join(args))
subprocess.run(args, check=True)
