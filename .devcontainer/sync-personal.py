#!/usr/bin/env python3
"""Sync personal-files changes onto bar/devcontainer, then rebase the current branch.

Workflow:
  1. From the current branch, pick out unstaged/staged changes whose paths are
     under PERSONAL_PATHS. Commit them on bar/devcontainer with the message
     passed via -m. Push.
  2. Return to the original branch and rebase onto bar/devcontainer. Push if
     the branch has a remote tracking ref.

Refuses to run if the rebase would touch files that are currently dirty
(personal or otherwise) — those would be lost.
"""

import argparse
import sys
from pathlib import Path

import git
from git import GitCommandError, Repo

PERSONAL_PATHS = [
    ".devcontainer",
    ".claude",
    "CLAUDE.md",
]

PERSONAL_BRANCH = "bar/devcontainer"


def is_personal(path: str) -> bool:
    p = Path(path)
    for personal in PERSONAL_PATHS:
        pp = Path(personal)
        if p == pp or pp in p.parents:
            return True
    return False


def changed_paths(repo: Repo) -> list[str]:
    """Return all paths with working-tree or index changes, plus untracked files."""
    paths: set[str] = set()
    # Modified/deleted/renamed in working tree vs index.
    for diff in repo.index.diff(None):
        paths.add(diff.b_path or diff.a_path)
    # Staged: index vs HEAD.
    for diff in repo.index.diff("HEAD"):
        paths.add(diff.b_path or diff.a_path)
    paths.update(repo.untracked_files)
    return sorted(paths)


def has_upstream(repo: Repo, branch_name: str) -> bool:
    try:
        branch = repo.heads[branch_name]
    except IndexError:
        return False
    try:
        return branch.tracking_branch() is not None
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-m", "--message", required=True,
                    help="Commit message for the personal-files commit.")
    args = ap.parse_args()

    repo = Repo(Path(__file__).resolve().parent.parent)
    current = repo.active_branch.name

    if current == PERSONAL_BRANCH:
        print(f"Already on {PERSONAL_BRANCH}; this script is for syncing FROM a feature branch.",
              file=sys.stderr)
        return 1

    all_changes = changed_paths(repo)
    personal_changes = [p for p in all_changes if is_personal(p)]
    other_changes = [p for p in all_changes if not is_personal(p)]

    if not personal_changes:
        print("No personal-files changes to sync.")
        return 0

    print(f"Personal changes ({len(personal_changes)}):")
    for p in personal_changes:
        print(f"  {p}")
    if other_changes:
        print(f"Other changes left untouched ({len(other_changes)}):")
        for p in other_changes:
            print(f"  {p}")

    # Upfront conflict check: if any "other" change is in a path that
    # bar/devcontainer also modifies relative to the merge-base, the rebase
    # would touch a dirty file. Refuse.
    if other_changes:
        merge_base = repo.merge_base("HEAD", PERSONAL_BRANCH)[0]
        diff_paths = {
            (d.b_path or d.a_path)
            for d in merge_base.diff(repo.heads[PERSONAL_BRANCH].commit)
        }
        risky = [p for p in other_changes if p in diff_paths]
        if risky:
            print("Refusing: rebase would touch dirty files:", file=sys.stderr)
            for p in risky:
                print(f"  {p}", file=sys.stderr)
            return 1

    g = repo.git
    stash_pushed = False

    try:
        # Stash everything (incl. untracked) so checkout is clean.
        g.stash("push", "--include-untracked", "-m", f"sync-personal: from {current}")
        stash_pushed = True

        g.checkout(PERSONAL_BRANCH)
        g.stash("pop")
        stash_pushed = False

        # Stage personal paths only.
        g.add("--", *personal_changes)
        g.commit("-m", args.message)
        print(f"Committed on {PERSONAL_BRANCH}: {args.message}")

        if has_upstream(repo, PERSONAL_BRANCH):
            print(g.push())
            print(f"Pushed {PERSONAL_BRANCH}")
        else:
            print(f"No upstream for {PERSONAL_BRANCH}; skipping push")

        # Re-stash leftovers so we can switch branches.
        leftover = changed_paths(repo)
        if leftover:
            g.stash("push", "--include-untracked", "-m",
                    f"sync-personal: leftover from {current}")
            stash_pushed = True

        g.checkout(current)

        if stash_pushed:
            g.stash("pop")
            stash_pushed = False

        try:
            g.rebase(PERSONAL_BRANCH)
        except GitCommandError as e:
            print("Rebase failed; aborting.", file=sys.stderr)
            print(e.stderr or str(e), file=sys.stderr)
            try:
                g.rebase("--abort")
            except GitCommandError:
                pass
            return 1

        print(f"Rebased {current} onto {PERSONAL_BRANCH}")

        if has_upstream(repo, current):
            print(g.push("--force-with-lease"))
            print(f"Pushed {current} (force-with-lease)")
        else:
            print(f"No upstream for {current}; skipping push")

    finally:
        if stash_pushed:
            print("Cleaning up: popping stash", file=sys.stderr)
            try:
                g.stash("pop")
            except GitCommandError as e:
                print(e.stderr or str(e), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
