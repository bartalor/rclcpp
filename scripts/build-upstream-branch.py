#!/usr/bin/env python3
"""Build/refresh an upstream-only sibling branch from a -dev branch.

Given a branch named `<name>-dev`, produce a sibling branch `<name>` that
contains the same commits *minus* personal-only commits (per
PR_EXCLUDED_PATHS in personal_paths.py).

This is the only thing the script does. It does NOT chase upstream/rolling,
push, or PR — those are separate concerns.

Algorithm
---------
1. Find the merge-base of <name>-dev with `upstream/rolling` (the common
   ancestor we know is upstream-clean). That base SHA is the starting
   point for the clean branch.
2. Walk commits from base..<name>-dev in order. For each commit, classify
   the paths it touches:
     - "upstream" → cherry-pick onto the clean branch.
     - "personal" → skip.
     - "mixed"    → ABORT (no upstream PR commit may touch personal paths).
     - "empty"    → skip (shouldn't happen with normal commits).
3. Move/create branch <name> at the resulting tip.

Re-runnable: each run rebuilds <name> from scratch off the current base.
The branch is force-updated locally only; pushing is the caller's job.
"""

import argparse
import sys
from pathlib import Path

from git import GitCommandError, Repo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from personal_paths import PR_EXCLUDED_PATHS, classify_paths

UPSTREAM_REF = "upstream/rolling"
DEV_SUFFIX = "-dev"


def commit_paths(repo: Repo, sha: str) -> list[str]:
    """All paths touched by commit `sha` (added/modified/deleted/renamed)."""
    out = repo.git.show("--name-only", "--pretty=format:", sha).strip()
    return [line for line in out.splitlines() if line]


def build_clean_branch(repo: Repo, dev_branch: str, clean_branch: str) -> int:
    g = repo.git

    if dev_branch not in [h.name for h in repo.heads]:
        print(f"Refusing: {dev_branch} does not exist locally.", file=sys.stderr)
        return 1

    try:
        base = g.merge_base(UPSTREAM_REF, dev_branch).strip()
    except GitCommandError as e:
        print(f"Refusing: no merge-base between {UPSTREAM_REF} and {dev_branch}: "
              f"{e.stderr or e}", file=sys.stderr)
        return 1

    dev_tip = repo.heads[dev_branch].commit.hexsha
    if base == dev_tip:
        print(f"{dev_branch} has no commits beyond {UPSTREAM_REF}; nothing to build.")
        return 1

    commits = list(repo.iter_commits(f"{base}..{dev_tip}", reverse=True))
    print(f"Walking {len(commits)} commits on {dev_branch} since "
          f"{UPSTREAM_REF} (base {base[:8]})")

    plan: list[tuple[str, str, str]] = []
    for c in commits:
        sha = c.hexsha
        subject = c.message.splitlines()[0]
        paths = commit_paths(repo, sha)
        kind = classify_paths(paths, PR_EXCLUDED_PATHS)
        plan.append((sha, kind, subject))
        if kind == "mixed":
            print(f"\nABORT: commit {sha[:8]} ({subject}) touches both upstream "
                  f"and personal paths:", file=sys.stderr)
            for p in paths:
                tag = "personal" if classify_paths([p], PR_EXCLUDED_PATHS) == "personal" else "upstream"
                print(f"  [{tag}] {p}", file=sys.stderr)
            print("\nSplit the commit so each one touches only one side, "
                  "then re-run.", file=sys.stderr)
            return 1

    upstream_count = sum(1 for _, k, _ in plan if k == "upstream")
    personal_count = sum(1 for _, k, _ in plan if k == "personal")
    print(f"  upstream: {upstream_count}, personal (skip): {personal_count}")

    if upstream_count == 0:
        print(f"\nNo upstream commits to put on {clean_branch}; "
              "leaving it untouched.")
        return 1

    head_before = repo.head.commit.hexsha if not repo.head.is_detached else None
    original_branch = (repo.active_branch.name
                       if not repo.head.is_detached else None)

    print(f"\nCreating {clean_branch} at {base[:8]}")
    try:
        g.checkout("--detach", base)
        for sha, kind, subject in plan:
            if kind != "upstream":
                continue
            print(f"  pick {sha[:8]} {subject}")
            try:
                g.cherry_pick(sha)
            except GitCommandError as e:
                print(f"\nCherry-pick failed at {sha[:8]}: {e.stderr or e}",
                      file=sys.stderr)
                g.cherry_pick("--abort")
                if original_branch:
                    g.checkout(original_branch)
                return 1

        new_tip = repo.head.commit.hexsha
        print(f"\n{clean_branch} -> {new_tip[:8]}")

        existing = [h.name for h in repo.heads]
        if clean_branch in existing:
            g.branch("-f", clean_branch, new_tip)
        else:
            g.branch(clean_branch, new_tip)
    finally:
        if original_branch:
            try:
                g.checkout(original_branch)
            except GitCommandError as e:
                print(f"Could not return to {original_branch}: "
                      f"{e.stderr or e}", file=sys.stderr)

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dev_branch",
                    help=f"Source branch ending in {DEV_SUFFIX} "
                         "(e.g. bar/issue-2898-dev)")
    args = ap.parse_args()

    if not args.dev_branch.endswith(DEV_SUFFIX):
        print(f"Refusing: source branch must end in {DEV_SUFFIX}",
              file=sys.stderr)
        return 1

    clean_branch = args.dev_branch[: -len(DEV_SUFFIX)]
    repo = Repo(Path(__file__).resolve().parent.parent)

    return build_clean_branch(repo, args.dev_branch, clean_branch)


if __name__ == "__main__":
    sys.exit(main())
