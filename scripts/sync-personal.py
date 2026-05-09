#!/usr/bin/env python3
"""Sync personal-files changes between feature branches and bar/devcontainer.

Three mutually-exclusive modes, all of which precheck everything and ABORT on
any problem before mutating anything:

  --commit-personal -m "msg"
    Commit currently-dirty personal-files (paths under PERSONAL_PATHS) on
    bar/devcontainer with the given message, push, then checkout back to the
    original branch. Refuses if non-personal files are dirty, if there are
    no personal changes, or if running on bar/devcontainer.

  --rebase-on-personal
    Rebase every other local branch onto bar/devcontainer (tree-aware: each
    branch's own commits replay on bar/devcontainer's current tip, no
    duplicates). Refuses on any dirty file.

  --rebase-on-rolling
    Fetch upstream/rolling, then rebase bar/devcontainer onto it AND every
    other local branch onto bar/devcontainer's new tip (tree-aware). Refuses
    on any dirty file or stale branch (where merge-base(child, parent) is
    not parent.tip — user must rebase manually first).

Every branch mutation is logged to scripts/.sync-personal-undo/<timestamp>.log
with paste-ready `git update-ref` revert lines (written BEFORE the mutation,
so a crash mid-script still leaves the undo trail on disk).
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
    """Record undo line for a branch BEFORE attempting to mutate it."""
    fh.write(f"# {op}: {branch}  pre={old_sha[:12]}\n")
    fh.write(f"git update-ref refs/heads/{branch} {old_sha}\n")
    fh.flush()


def rebase_branch(repo: Repo, log_fh: TextIO, branch: str,
                  rebase_args: list[str], op_label: str) -> bool:
    """Checkout `branch`, log pre-SHA, run `git rebase <rebase_args>`."""
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


def _has_merge_commit(repo: Repo, base: str, tip: str) -> bool:
    return any(len(c.parents) > 1 for c in repo.iter_commits(f"{base}..{tip}"))


def build_branch_tree(repo: Repo, new_base: str,
                      include_personal: bool) -> dict[str, str]:
    """Return the explicit branch tree by repo convention.

    If include_personal:
      - bar/devcontainer is rooted on new_base.
      - Every other local branch is stacked on bar/devcontainer.
    Else (used for --rebase-on-personal where new_base == bar/devcontainer):
      - bar/devcontainer is excluded.
      - Every other local branch is rooted on new_base (i.e. bar/devcontainer).
    """
    tree: dict[str, str] = {}
    local_names = {h.name for h in repo.heads}
    if PERSONAL_BRANCH not in local_names:
        return tree
    if include_personal:
        tree[PERSONAL_BRANCH] = new_base
    for h in repo.heads:
        name = h.name
        if name == PERSONAL_BRANCH:
            continue
        if name == UPSTREAM_BRANCH:
            continue
        tree[name] = PERSONAL_BRANCH if include_personal else new_base
    return tree


def precheck_rebase_tree(repo: Repo, tree: dict[str, str],
                         new_base: str) -> list[str]:
    """Validate that the declared `tree` is rebase-safe.

    Returns a list of problems. Empty = safe to proceed. Non-empty = abort.

    Hard rule: every child's branch-point relative to its declared parent
    must equal its parent's CURRENT tip. If the parent has any commits past
    the branch-point, the child is stale — abort.
    """
    problems: list[str] = []

    try:
        new_base_sha = repo.commit(new_base).hexsha
    except Exception as e:
        problems.append(f"new_base does not resolve: {new_base} ({e})")
        return problems

    local_names = {h.name for h in repo.heads}
    for branch in tree:
        if branch not in local_names:
            problems.append(f"branch in tree does not exist locally: {branch}")

    for branch, parent_ref in tree.items():
        if parent_ref == new_base:
            continue
        if parent_ref not in tree:
            problems.append(
                f"{branch}'s declared parent '{parent_ref}' is not in the tree")

    if problems:
        return problems

    branch_shas = {b: repo.heads[b].commit.hexsha for b in tree}

    for branch, parent_ref in tree.items():
        tip = branch_shas[branch]
        parent_tip = (new_base_sha if parent_ref == new_base
                      else branch_shas[parent_ref])

        if _has_merge_commit(repo, parent_tip, tip):
            problems.append(
                f"{branch} contains merge commits in {parent_ref}..{branch}; "
                f"rebase_tree only handles linear history")
            continue

        try:
            mb = repo.git.merge_base(tip, parent_tip).strip()
        except GitCommandError:
            problems.append(f"{branch} has no merge-base with {parent_ref}")
            continue

        if mb != parent_tip:
            ahead = sum(1 for _ in repo.iter_commits(f"{mb}..{parent_tip}"))
            problems.append(
                f"{branch} is stale relative to its declared parent "
                f"'{parent_ref}': branch-point is {mb[:8]} but parent tip is "
                f"{parent_tip[:8]} ({ahead} commit(s) ahead). Rebase "
                f"{branch} onto {parent_ref} manually first.")

    return problems


def _topo_sort_tree(tree: dict[str, str], new_base: str) -> list[str]:
    """Order branches parents-first. Roots (parent == new_base) come first."""
    ordered: list[str] = []
    remaining = set(tree)
    while remaining:
        progress = False
        for b in list(remaining):
            p = tree[b]
            if p == new_base or p in ordered:
                ordered.append(b)
                remaining.remove(b)
                progress = True
        if not progress:
            ordered.extend(remaining)
            break
    return ordered


def _descendants_of(tree: dict[str, str], branch: str) -> list[str]:
    out: list[str] = []
    pending = [branch]
    while pending:
        cur = pending.pop()
        for b, p in tree.items():
            if p == cur and b not in out:
                out.append(b)
                pending.append(b)
    return out


def rebase_tree(repo: Repo, log_fh: TextIO, tree: dict[str, str],
                new_base: str) -> tuple[bool, list[str]]:
    """Rebase every branch in `tree` onto its declared parent's new tip.

    Pre-checks the entire tree; aborts pre-mutation on any failure. On any
    rebase OR push failure mid-run, breaks immediately — descendants are
    marked failed and not touched.
    """
    problems = precheck_rebase_tree(repo, tree, new_base)
    if problems:
        print("Pre-check failed; refusing to touch any branch:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return False, []

    g = repo.git
    new_base_sha = repo.commit(new_base).hexsha
    order = _topo_sort_tree(tree, new_base)

    old_tip = {b: repo.heads[b].commit.hexsha for b in tree}
    new_tip: dict[str, str] = {}
    failed: list[str] = []

    for b in order:
        parent_ref = tree[b]
        old_parent_sha = (new_base_sha if parent_ref == new_base
                          else old_tip[parent_ref])
        new_parent_sha = (new_base_sha if parent_ref == new_base
                          else new_tip[parent_ref])

        print(f"\n=== {b} ===")
        print(f"  parent: {parent_ref}")
        print(f"  pre-rebase: {old_tip[b][:8]}")
        print(f"  --onto {new_parent_sha[:8]} {old_parent_sha[:8]}")

        if old_parent_sha == new_parent_sha:
            print("  parent unchanged; nothing to do")
            new_tip[b] = old_tip[b]
            continue

        ok = rebase_branch(repo, log_fh, b,
                           ["--onto", new_parent_sha, old_parent_sha, b],
                           f"rebase --onto {new_parent_sha[:8]} {old_parent_sha[:8]}")
        if not ok:
            failed.append(b)
            for d in _descendants_of(tree, b):
                if d not in failed:
                    failed.append(d)
            break

        new_tip[b] = repo.heads[b].commit.hexsha
        print(f"  post-rebase: {new_tip[b][:8]}")

        if has_upstream(repo, b):
            try:
                g.push("--force-with-lease")
                print("  pushed (force-with-lease)")
            except GitCommandError as e:
                print(f"Push failed: {e.stderr or e}", file=sys.stderr)
                failed.append(b)
                for d in _descendants_of(tree, b):
                    if d not in failed:
                        failed.append(d)
                break
        else:
            print("  no upstream; skipping push")

    return len(failed) == 0, failed


def is_personal(path: str) -> bool:
    p = Path(path)
    if any(part == ".." for part in p.parts):
        raise ValueError(f"path contains '..': {path!r}")
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


def has_remote(repo: Repo, name: str) -> bool:
    return any(r.name == name for r in repo.remotes)


def commit_personal(repo: Repo, message: str) -> int:
    """Commit dirty personal files on bar/devcontainer, push, checkout back.

    Prechecks (all run; first failure aborts; no mutations):
      - Not currently on bar/devcontainer.
      - bar/devcontainer exists locally.
      - No non-personal files are dirty.
      - At least one personal file is dirty.
      - All dirty paths classify cleanly (no path-resolution errors).
    """
    if PERSONAL_BRANCH not in [h.name for h in repo.heads]:
        print(f"Refusing: {PERSONAL_BRANCH} does not exist locally.",
              file=sys.stderr)
        return 1

    current = repo.active_branch.name
    if current == PERSONAL_BRANCH:
        print(f"Refusing: already on {PERSONAL_BRANCH}; "
              "this mode is for syncing FROM a feature branch.",
              file=sys.stderr)
        return 1

    all_changes = changed_paths(repo)
    try:
        personal_changes = [p for p in all_changes if is_personal(p)]
        other_changes = [p for p in all_changes if not is_personal(p)]
    except ValueError as e:
        print(f"Refusing: cannot classify path: {e}", file=sys.stderr)
        return 1

    if other_changes:
        print("Refusing: non-personal files are dirty:", file=sys.stderr)
        for p in other_changes:
            print(f"  {p}", file=sys.stderr)
        return 1

    if not personal_changes:
        print("Refusing: no personal-files changes to commit.", file=sys.stderr)
        return 1

    print(f"Personal changes ({len(personal_changes)}):")
    for p in personal_changes:
        print(f"  {p}")

    log_path, log_fh = open_undo_log(repo)
    print(f"Undo log: {log_path}")

    g = repo.git
    pre_devc = repo.heads[PERSONAL_BRANCH].commit.hexsha
    log_branch_pre_change(log_fh, PERSONAL_BRANCH, pre_devc, "personal-files commit")
    try:
        g.checkout(PERSONAL_BRANCH)
        g.add("--", *personal_changes)
        g.commit("-m", message)
    except GitCommandError as e:
        print(f"Commit failed: {e.stderr or e}", file=sys.stderr)
        log_fh.close()
        return 1

    print(f"Committed on {PERSONAL_BRANCH}: {message}")

    if has_upstream(repo, PERSONAL_BRANCH):
        try:
            g.push()
            print(f"Pushed {PERSONAL_BRANCH}")
        except GitCommandError as e:
            print(f"Push failed: {e.stderr or e}", file=sys.stderr)
            log_fh.close()
            return 1
    else:
        print(f"No upstream for {PERSONAL_BRANCH}; skipping push")

    try:
        g.checkout(current)
        print(f"Checked out back to {current}")
    except GitCommandError as e:
        print(f"Checkout back to {current} failed: {e.stderr or e}",
              file=sys.stderr)
        log_fh.close()
        return 1

    log_fh.close()
    print(f"\nUndo log written: {log_path}")
    return 0


def rebase_on_personal(repo: Repo) -> int:
    """Rebase every other local branch onto bar/devcontainer.

    Prechecks: clean tree, bar/devcontainer exists. Tree-aware rebase
    aborts pre-mutation on any tree problem.
    """
    dirty = changed_paths(repo)
    if dirty:
        print("Refusing: working tree is not clean.", file=sys.stderr)
        for p in dirty:
            print(f"  {p}", file=sys.stderr)
        return 1

    if PERSONAL_BRANCH not in [h.name for h in repo.heads]:
        print(f"Refusing: {PERSONAL_BRANCH} does not exist locally.",
              file=sys.stderr)
        return 1

    tree = build_branch_tree(repo, PERSONAL_BRANCH, include_personal=False)
    if not tree:
        print("Refusing: nothing to rebase.", file=sys.stderr)
        return 1

    return _run_tree_rebase(repo, tree, PERSONAL_BRANCH)


def rebase_on_rolling(repo: Repo) -> int:
    """Rebase bar/devcontainer + every other local branch onto upstream/rolling.

    Prechecks: clean tree, bar/devcontainer exists, upstream remote exists.
    Then fetch (read-only network), then tree-aware rebase which aborts
    pre-mutation on any tree problem.
    """
    dirty = changed_paths(repo)
    if dirty:
        print("Refusing: working tree is not clean.", file=sys.stderr)
        for p in dirty:
            print(f"  {p}", file=sys.stderr)
        return 1

    if PERSONAL_BRANCH not in [h.name for h in repo.heads]:
        print(f"Refusing: {PERSONAL_BRANCH} does not exist locally.",
              file=sys.stderr)
        return 1

    if not has_remote(repo, UPSTREAM_REMOTE):
        print(f"Refusing: remote '{UPSTREAM_REMOTE}' does not exist.",
              file=sys.stderr)
        return 1

    print(f"Fetching {UPSTREAM_REF}...")
    try:
        repo.git.fetch(UPSTREAM_REMOTE, UPSTREAM_BRANCH)
    except GitCommandError as e:
        print(f"Fetch failed: {e.stderr or e}", file=sys.stderr)
        return 1

    tree = build_branch_tree(repo, UPSTREAM_REF, include_personal=True)
    if not tree:
        print("Refusing: nothing to rebase.", file=sys.stderr)
        return 1

    return _run_tree_rebase(repo, tree, UPSTREAM_REF)


def _run_tree_rebase(repo: Repo, tree: dict[str, str], new_base: str) -> int:
    """Shared driver: precheck (via rebase_tree), rebase, restore branch.

    Opens the undo log AFTER the precheck would have a chance to run, so an
    abort doesn't write a near-empty file. To preserve that, we run a dry
    precheck here first.
    """
    problems = precheck_rebase_tree(repo, tree, new_base)
    if problems:
        print("Pre-check failed; refusing to touch any branch:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    original = repo.active_branch.name
    log_path, log_fh = open_undo_log(repo)
    print(f"Undo log: {log_path}")
    print("=== Pre-change branch state ===")
    for h in repo.heads:
        subject = h.commit.message.splitlines()[0]
        print(f"  {h.name:30s} {h.commit.hexsha[:8]}  {subject}")
    print()
    print("=== Declared tree ===")
    for b, p in tree.items():
        print(f"  {b} -> {p}")
    print()

    ok, failed = rebase_tree(repo, log_fh, tree, new_base)

    try:
        repo.git.checkout(original)
    except GitCommandError as e:
        print(f"Could not return to {original}: {e.stderr or e}",
              file=sys.stderr)

    log_fh.close()
    print(f"\nUndo log written: {log_path}")

    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--commit-personal", action="store_true",
                      help="Commit dirty personal files on bar/devcontainer "
                           "and push. Requires -m.")
    mode.add_argument("--rebase-on-personal", action="store_true",
                      help="Rebase every other local branch onto bar/devcontainer.")
    mode.add_argument("--rebase-on-rolling", action="store_true",
                      help=f"Rebase bar/devcontainer onto {UPSTREAM_REF} and "
                           "every other local branch onto bar/devcontainer.")
    ap.add_argument("-m", "--message",
                    help="Commit message (required for --commit-personal).")
    args = ap.parse_args()

    repo = Repo(Path(__file__).resolve().parent.parent)

    if args.commit_personal:
        if not args.message:
            ap.error("--commit-personal requires -m/--message")
        return commit_personal(repo, args.message)

    if args.rebase_on_personal:
        return rebase_on_personal(repo)

    if args.rebase_on_rolling:
        return rebase_on_rolling(repo)

    ap.error("no mode selected")  # unreachable; group is required
    return 1


if __name__ == "__main__":
    sys.exit(main())
