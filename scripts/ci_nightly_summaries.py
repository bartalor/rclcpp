#!/usr/bin/env python3
"""Fetch slim test-outcome summaries (no logs) from ci.ros2.org, lazily cached.

Usage:
  ci_nightly_summaries.py <job> <build>          # fetch one specific build
  ci_nightly_summaries.py <job> --recent N       # fetch N most recent builds

Auth: relies on ~/.netrc for ci.ros2.org (machine/login/password=<token>).
Cache: .ci-cache/<job>/<build>.json at the repo root.
"""
from __future__ import annotations

import argparse
import json
import netrc
import sys
import urllib.error
import urllib.request
from pathlib import Path

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


def list_builds(auth: str, job: str, n: int) -> list[dict]:
    url = f"{BASE}/job/{job}/api/json?tree=builds[number,result,timestamp]"
    data = json.loads(http_get(url, auth))
    return data["builds"][:n]


def fetch_test_report(auth: str, job: str, build: int) -> dict | None:
    cache = CACHE_ROOT / job / f"{build}.json"
    if cache.exists():
        return json.loads(cache.read_bytes())
    url = (
        f"{BASE}/job/{job}/{build}/testReport/api/json"
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


def print_summary(build: int, result: str | None, report: dict | None) -> None:
    if report is None:
        print(f"  build {build}: {result}  (no testReport)")
        return
    print(
        f"  build {build}: {result}  "
        f"pass={report.get('passCount')} fail={report.get('failCount')} "
        f"skip={report.get('skipCount')}"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("job")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("build", nargs="?", type=int)
    g.add_argument("--recent", type=int, metavar="N")
    args = p.parse_args()

    auth = auth_header()

    if args.build is not None:
        report = fetch_test_report(auth, args.job, args.build)
        print(f"# {args.job}/{args.build}")
        print_summary(args.build, None, report)
        return 0

    builds = list_builds(auth, args.job, args.recent)
    print(f"# {args.job}: {len(builds)} recent builds")
    for b in builds:
        n = b["number"]
        report = fetch_test_report(auth, args.job, n)
        print_summary(n, b.get("result"), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
