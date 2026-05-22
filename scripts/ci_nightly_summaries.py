#!/usr/bin/env python3
"""Fetch slim test-outcome summaries (no logs) from ci.ros2.org nightlies, lazily cached.

Auth: relies on ~/.netrc for ci.ros2.org (machine/login/password=<token>).
Cache: .ci-cache/<job>/<build>.json at the repo root.
"""
from __future__ import annotations

import json
import netrc
import sys
import urllib.request
from pathlib import Path

JOB = "nightly_win_rel"
N_BUILDS = 20
BASE = "https://ci.ros2.org"
CACHE_ROOT = Path(__file__).resolve().parent.parent / ".ci-cache"


def auth_header() -> str:
    rc = netrc.netrc()
    creds = rc.authenticators("ci.ros2.org")
    if not creds:
        sys.exit("no ci.ros2.org entry in ~/.netrc")
    login, _, token = creds
    import base64
    raw = f"{login}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def http_get(url: str, auth: str) -> bytes:
    req = urllib.request.Request(url, headers={"Authorization": auth})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def list_builds(auth: str, n: int) -> list[dict]:
    url = f"{BASE}/job/{JOB}/api/json?tree=builds[number,result,timestamp]"
    data = json.loads(http_get(url, auth))
    return data["builds"][:n]


def fetch_test_report(auth: str, build: int) -> dict | None:
    cache = CACHE_ROOT / JOB / f"{build}.json"
    if cache.exists():
        return json.loads(cache.read_bytes())
    url = (
        f"{BASE}/job/{JOB}/{build}/testReport/api/json"
        "?tree=failCount,passCount,skipCount,suites[cases[className,name,status]]"
    )
    try:
        body = http_get(url, auth)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return json.loads(body)


def main() -> int:
    auth = auth_header()
    builds = list_builds(auth, N_BUILDS)
    print(f"# {JOB}: {len(builds)} recent builds")
    for b in builds:
        n = b["number"]
        result = b.get("result")
        report = fetch_test_report(auth, n)
        if report is None:
            print(f"  build {n}: {result}  (no testReport)")
            continue
        print(
            f"  build {n}: {result}  "
            f"pass={report.get('passCount')} fail={report.get('failCount')} "
            f"skip={report.get('skipCount')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
