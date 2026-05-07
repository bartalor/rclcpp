#!/usr/bin/env python3
"""Sync personal-files changes onto bar/devcontainer, then rebase the current branch.

Workflow:
  1. From the current branch, pick out unstaged/staged changes whose paths are
     under PERSONAL_PATHS. Commit them on bar/devcontainer with the message
     passed via -m. Push.
  2. Return to the original branch and rebase onto bar/devcontainer. Push if
     the branch has a remote tracking ref.

Refuses to run if non-personal files are dirty (rebase needs a clean tree).
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
    for diff in repo.index.diff(None):
        paths.add(diff.b_path or diff.a_path)
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


def commits_ahead(repo: Repo, ahead: str, behind: str) -> int:
    """How many commits `ahead` has that `behind` doesn't."""
    return sum(1 for _ in repo.iter_commits(f"{behind}..{ahead}"))


def prompt_yes_no(question: str) -> bool:
    while True:
        ans = input(f"{question} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
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

    ahead = commits_ahead(repo, PERSONAL_BRANCH, current)
    if ahead > 0:
        print(f"{PERSONAL_BRANCH} is {ahead} commit(s) ahead of {current}.")
        if not prompt_yes_no(f"Rebase {current} onto {PERSONAL_BRANCH} first?"):
            print("Aborted.")
            return 1
        g = repo.git
        try:
            g.rebase(PERSONAL_BRANCH)
        except GitCommandError as e:
            print("Pre-rebase failed; aborting.", file=sys.stderr)
            print(e.stderr or str(e), file=sys.stderr)
            try:
                g.rebase("--abort")
            except GitCommandError:
                pass
            return 1
        print(f"Rebased {current} onto {PERSONAL_BRANCH}")

    all_changes = changed_paths(repo)
    personal_changes = [p for p in all_changes if is_personal(p)]
    other_changes = [p for p in all_changes if not is_personal(p)]

    if other_changes:
        print("Refusing: non-personal files are dirty (rebase needs a clean tree):",
              file=sys.stderr)
        for p in other_changes:
            print(f"  {p}", file=sys.stderr)
        return 1

    if not personal_changes:
        print("No personal-files changes to sync.")
        return 0

    print(f"Personal changes ({len(personal_changes)}):")
    for p in personal_changes:
        print(f"  {p}")

    g = repo.git
    g.checkout(PERSONAL_BRANCH)
    g.add("--", *personal_changes)
    g.commit("-m", args.message)
    print(f"Committed on {PERSONAL_BRANCH}: {args.message}")

    if has_upstream(repo, PERSONAL_BRANCH):
        print(g.push())
        print(f"Pushed {PERSONAL_BRANCH}")
    else:
        print(f"No upstream for {PERSONAL_BRANCH}; skipping push")

    g.checkout(current)

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
