#!/usr/bin/env python3
"""Sync personal-files changes onto bar/devcontainer, then rebase the current branch.

Default workflow:
  1. From the current branch, pick out unstaged/staged changes whose paths are
     under PERSONAL_PATHS. Commit them on bar/devcontainer with the message
     passed via -m. Push.
  2. Return to the original branch and rebase onto bar/devcontainer. Push if
     the branch has a remote tracking ref.

With --rebase-on-rolling: fetch upstream/rolling, rebase bar/devcontainer
onto it, then for every other local branch based on the OLD bar/devcontainer
tip, rebase with `--onto NEW_DEVC OLD_DEVC <branch>` so only the branch's
own commits replay (no duplicate personal commits). Each touched branch is
force-with-lease pushed if it has an upstream. Branches not based on
bar/devcontainer are skipped with a warning.

Refuses to run if non-personal files are dirty in the default flow, or if
ANY file is dirty in --rebase-on-rolling. Every branch mutation is logged
to scripts/.sync-personal-undo/<timestamp>.log with paste-ready
`git update-ref` revert lines (written BEFORE the mutation, so a crash
mid-script still leaves the undo trail on disk).
"""

import argparse
import datetime as _dt
import sys
from pathlib import Path
from typing import TextIO

from git import GitCommandError, Repo

PERSONAL_PATHS = [
    ".devcontainer",
    ".claude",
    "scripts",
    "CLAUDE.md",
]

PERSONAL_BRANCH = "bar/devcontainer"
UPSTREAM_REMOTE = "upstream"
UPSTREAM_BRANCH = "rolling"
UPSTREAM_REF = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
UNDO_LOG_DIR = Path(__file__).resolve().parent / ".sync-personal-undo"


def open_undo_log(repo: Repo) -> tuple[Path, TextIO]:
    """Open a fresh undo log file for this run. Logs every branch change."""
    UNDO_LOG_DIR.mkdir(exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = UNDO_LOG_DIR / f"{ts}.log"
    fh = path.open("w")
    fh.write(f"# sync-personal.py undo log: {ts}\n")
    fh.write(f"# argv: {sys.argv}\n")
    fh.write("# Initial branch state (paste lines below to revert):\n")
    for h in repo.heads:
        fh.write(f"git update-ref refs/heads/{h.name} {h.commit.hexsha}  "
                 f"# {h.commit.message.splitlines()[0]}\n")
    fh.write("#\n# Live branch updates follow:\n")
    fh.flush()
    return path, fh


def log_branch_pre_change(fh: TextIO, branch: str, old_sha: str, op: str) -> None:
    """Record undo line for a branch BEFORE attempting to mutate it.

    Writes the `git update-ref` revert line first so that even if the script
    crashes between this call and the rebase, the user can recover.
    """
    fh.write(f"# {op}: {branch}  pre={old_sha[:12]}\n")
    fh.write(f"git update-ref refs/heads/{branch} {old_sha}\n")
    fh.flush()


def rebase_branch(repo: Repo, log_fh: TextIO, branch: str,
                  rebase_args: list[str], op_label: str) -> bool:
    """Checkout `branch`, log pre-SHA, run `git rebase <rebase_args>`.

    Returns True on success. On rebase failure: prints, aborts, returns False.
    Caller handles push + post-rebase reporting.
    """
    g = repo.git
    pre_sha = repo.heads[branch].commit.hexsha
    log_branch_pre_change(log_fh, branch, pre_sha, op_label)
    try:
        g.checkout(branch)
        g.rebase(*rebase_args)
    except GitCommandError as e:
        print(f"Rebase failed: {e.stderr or e}", file=sys.stderr)
        try:
            g.rebase("--abort")
        except GitCommandError:
            pass
        return False
    return True


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


def rebase_all_on_rolling(repo: Repo) -> int:
    """Rebase the dependency tree onto upstream/rolling, preserving structure.

    The tree is: upstream/rolling <- bar/devcontainer <- feature branches.
    Step 1: rebase bar/devcontainer onto upstream/rolling.
    Step 2: for every other local branch based on the OLD bar/devcontainer,
    rebase with `--onto NEW_DEVC OLD_DEVC <branch>` so only the branch's own
    commits replay (no duplicates of personal commits).

    A branch not based on bar/devcontainer is skipped with a warning.
    """
    dirty = changed_paths(repo)
    if dirty:
        print("Refusing: working tree is not clean.", file=sys.stderr)
        for p in dirty:
            print(f"  {p}", file=sys.stderr)
        return 1

    g = repo.git
    original = repo.active_branch.name

    pre_state: dict[str, str] = {h.name: h.commit.hexsha for h in repo.heads}

    if PERSONAL_BRANCH not in pre_state:
        print(f"Refusing: {PERSONAL_BRANCH} does not exist locally.", file=sys.stderr)
        return 1

    print(f"Fetching {UPSTREAM_REF}...")
    try:
        g.fetch(UPSTREAM_REMOTE, UPSTREAM_BRANCH)
    except GitCommandError as e:
        print(f"Fetch failed: {e.stderr or e}", file=sys.stderr)
        return 1

    log_path, log_fh = open_undo_log(repo)
    print(f"Undo log: {log_path}")
    print("=== Pre-change branch state ===")
    for name, sha in pre_state.items():
        subject = repo.commit(sha).message.splitlines()[0]
        print(f"  {name:30s} {sha[:8]}  {subject}")
    print()

    old_devc = pre_state[PERSONAL_BRANCH]
    failed: list[str] = []
    skipped: list[str] = []

    print(f"=== {PERSONAL_BRANCH} ===")
    print(f"  pre-rebase: {old_devc[:8]}")
    if not rebase_branch(repo, log_fh, PERSONAL_BRANCH, [UPSTREAM_REF],
                         "rebase onto upstream/rolling"):
        print(f"\nAborting: {PERSONAL_BRANCH} rebase failed; no other branches touched.",
              file=sys.stderr)
        try:
            g.checkout(original)
        except GitCommandError:
            pass
        log_fh.close()
        return 1

    new_devc = repo.heads[PERSONAL_BRANCH].commit.hexsha
    print(f"  post-rebase: {new_devc[:8]}")
    if has_upstream(repo, PERSONAL_BRANCH):
        try:
            g.push("--force-with-lease")
            print(f"  pushed (force-with-lease)")
        except GitCommandError as e:
            print(f"Push failed: {e.stderr or e}", file=sys.stderr)
            failed.append(PERSONAL_BRANCH)
    else:
        print(f"  no upstream; skipping push")

    other_branches = [
        name for name in pre_state
        if name != PERSONAL_BRANCH and name != UPSTREAM_BRANCH
    ]

    for branch in other_branches:
        print(f"\n=== {branch} ===")
        branch_sha = pre_state[branch]
        print(f"  pre-rebase: {branch_sha[:8]}")
        try:
            g.merge_base("--is-ancestor", old_devc, branch_sha)
        except GitCommandError:
            print(f"  not based on {PERSONAL_BRANCH}@{old_devc[:8]}; skipping",
                  file=sys.stderr)
            skipped.append(branch)
            continue

        if not rebase_branch(repo, log_fh, branch,
                             ["--onto", new_devc, old_devc, branch],
                             f"rebase --onto {new_devc[:8]} {old_devc[:8]}"):
            failed.append(branch)
            continue
        new_sha = repo.heads[branch].commit.hexsha
        print(f"  post-rebase: {new_sha[:8]}")
        if has_upstream(repo, branch):
            try:
                g.push("--force-with-lease")
                print(f"  pushed (force-with-lease)")
            except GitCommandError as e:
                print(f"Push failed: {e.stderr or e}", file=sys.stderr)
                failed.append(branch)
        else:
            print(f"  no upstream; skipping push")

    try:
        g.checkout(original)
    except GitCommandError as e:
        print(f"Could not return to {original}: {e.stderr or e}", file=sys.stderr)

    log_fh.close()
    print(f"\nUndo log written: {log_path}")

    if skipped:
        print(f"\nSkipped (not based on {PERSONAL_BRANCH}): {', '.join(skipped)}")
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-m", "--message",
                    help="Commit message for the personal-files commit.")
    ap.add_argument("--rebase-on-rolling", action="store_true",
                    help=f"Rebase every local branch onto {UPSTREAM_REF} and push. "
                         "Ignores -m and the personal-files flow.")
    args = ap.parse_args()

    repo = Repo(Path(__file__).resolve().parent.parent)

    if args.rebase_on_rolling:
        return rebase_all_on_rolling(repo)

    if not args.message:
        ap.error("-m/--message is required unless --rebase-on-rolling is given")

    current = repo.active_branch.name

    if current == PERSONAL_BRANCH:
        print(f"Already on {PERSONAL_BRANCH}; this script is for syncing FROM a feature branch.",
              file=sys.stderr)
        return 1

    log_path, log_fh = open_undo_log(repo)
    print(f"Undo log: {log_path}")

    ahead = commits_ahead(repo, PERSONAL_BRANCH, current)
    if ahead > 0:
        print(f"{PERSONAL_BRANCH} is {ahead} commit(s) ahead of {current}.")
        if not prompt_yes_no(f"Rebase {current} onto {PERSONAL_BRANCH} first?"):
            print("Aborted.")
            log_fh.close()
            return 1
        if not rebase_branch(repo, log_fh, current, [PERSONAL_BRANCH],
                             f"pre-rebase onto {PERSONAL_BRANCH}"):
            log_fh.close()
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
        log_fh.close()
        return 1

    if not personal_changes:
        print("No personal-files changes to sync.")
        log_fh.close()
        return 0

    print(f"Personal changes ({len(personal_changes)}):")
    for p in personal_changes:
        print(f"  {p}")

    g = repo.git
    pre_devc = repo.heads[PERSONAL_BRANCH].commit.hexsha
    log_branch_pre_change(log_fh, PERSONAL_BRANCH, pre_devc, "personal-files commit")
    g.checkout(PERSONAL_BRANCH)
    g.add("--", *personal_changes)
    g.commit("-m", args.message)
    print(f"Committed on {PERSONAL_BRANCH}: {args.message}")

    if has_upstream(repo, PERSONAL_BRANCH):
        print(g.push())
        print(f"Pushed {PERSONAL_BRANCH}")
    else:
        print(f"No upstream for {PERSONAL_BRANCH}; skipping push")

    if not rebase_branch(repo, log_fh, current, [PERSONAL_BRANCH],
                         f"rebase onto {PERSONAL_BRANCH}"):
        log_fh.close()
        return 1

    print(f"Rebased {current} onto {PERSONAL_BRANCH}")

    if has_upstream(repo, current):
        print(g.push("--force-with-lease"))
        print(f"Pushed {current} (force-with-lease)")
    else:
        print(f"No upstream for {current}; skipping push")

    log_fh.close()
    print(f"\nUndo log written: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
