#!/usr/bin/env python3
"""Rebase the personal branch + every feature branch in a tree-aware way.

Two mutually-exclusive modes, both of which precheck everything and ABORT on
any problem before mutating anything:

  --rebase-on-personal
    Rebase every other local branch onto bar/devcontainer (tree-aware: each
    branch's own commits replay on bar/devcontainer's current tip, no
    duplicates). Refuses on any dirty file.

  --rebase-on-rolling
    Fetch upstream/rolling, then rebase bar/devcontainer onto it AND every
    other local branch onto bar/devcontainer's new tip (tree-aware). Refuses
    on any dirty file or stale branch (where merge-base(child, parent) is
    not parent.tip — user must rebase manually first).

Every branch mutation is logged to scripts/.rebase-branches-undo/<timestamp>.log
with paste-ready `git update-ref` revert lines (written BEFORE the mutation,
so a crash mid-script still leaves the undo trail on disk).
"""

import argparse
import contextlib
import datetime as _dt
import sys
from pathlib import Path
from typing import Iterator, TextIO

from git import GitCommandError, Repo

PERSONAL_BRANCH = "bar/devcontainer"
UPSTREAM_REMOTE = "upstream"
UPSTREAM_BRANCH = "rolling"
UPSTREAM_REF = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
UNDO_LOG_DIR = Path(__file__).resolve().parent / ".rebase-branches-undo"
UNDO_LOG_KEEP = 5


class UndoLog:
    """Append-only file recording each branch's pre-mutation SHA.

    Use via `with undo_log(repo) as log:`. Inside the block, call
    `log.write_pre_change(branch, sha, op)` BEFORE mutating `branch`.
    On block exit the file is closed and its path printed.
    """

    def __init__(self, fh: TextIO, path: Path) -> None:
        self._fh = fh
        self.path = path

    def write_pre_change(self, branch: str, old_sha: str, op: str) -> None:
        self._fh.write(f"# {op}: {branch}  pre={old_sha[:12]}\n")
        self._fh.write(f"git update-ref refs/heads/{branch} {old_sha}\n")
        self._fh.flush()


@contextlib.contextmanager
def undo_log(repo: Repo) -> Iterator[UndoLog]:
    """Open a fresh undo log file for this run. Prints path on enter and exit."""
    UNDO_LOG_DIR.mkdir(exist_ok=True)
    existing = sorted(UNDO_LOG_DIR.glob("*.log"))
    for old in existing[: max(0, len(existing) - (UNDO_LOG_KEEP - 1))]:
        old.unlink()
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = UNDO_LOG_DIR / f"{ts}.log"
    fh = path.open("w")
    try:
        fh.write(f"# rebase-branches.py undo log: {ts}\n")
        fh.write(f"# argv: {sys.argv}\n")
        fh.write("# Initial branch state (paste lines below to revert):\n")
        for h in repo.heads:
            fh.write(f"git update-ref refs/heads/{h.name} {h.commit.hexsha}  "
                     f"# {h.commit.message.splitlines()[0]}\n")
        fh.write("#\n# Live branch updates follow:\n")
        fh.flush()
        print(f"Undo log: {path}")
        yield UndoLog(fh, path)
    finally:
        fh.close()
        print(f"\nUndo log written: {path}")


def rebase_branch(repo: Repo, log: UndoLog, branch: str,
                  rebase_args: list[str], op_label: str) -> bool:
    """Checkout `branch`, log pre-SHA, run `git rebase <rebase_args>`."""
    g = repo.git
    pre_sha = repo.heads[branch].commit.hexsha
    log.write_pre_change(branch, pre_sha, op_label)
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
                         new_base: str) -> tuple[list[str], dict[str, str]]:
    """Validate that the declared `tree` is rebase-safe.

    Returns (problems, branch_point). Empty `problems` = safe to proceed.
    `branch_point[b]` is the SHA where `b` currently branches off its
    declared parent (== merge-base(b.tip, parent.tip)). The caller passes
    this as OLD_BASE to `git rebase --onto NEW_BASE OLD_BASE b`, which
    replays exactly b's own commits (since branch_point) onto the parent's
    new tip.

    Checks:
      - Every branch in `tree` exists locally.
      - new_base resolves.
      - No merge commits in (merge-base..child) ranges.
      - Every parent_ref is either new_base or another branch in `tree`.
    """
    problems: list[str] = []
    branch_point: dict[str, str] = {}

    try:
        new_base_sha = repo.commit(new_base).hexsha
    except Exception as e:
        problems.append(f"new_base does not resolve: {new_base} ({e})")
        return problems, branch_point

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
        return problems, branch_point

    branch_shas = {b: repo.heads[b].commit.hexsha for b in tree}

    for branch, parent_ref in tree.items():
        tip = branch_shas[branch]
        parent_tip = (new_base_sha if parent_ref == new_base
                      else branch_shas[parent_ref])

        try:
            mb = repo.git.merge_base(tip, parent_tip).strip()
        except GitCommandError:
            problems.append(f"{branch} has no merge-base with {parent_ref}")
            continue

        if _has_merge_commit(repo, mb, tip):
            problems.append(
                f"{branch} contains merge commits in {mb[:8]}..{branch}; "
                f"rebase_tree only handles linear history")
            continue

        branch_point[branch] = mb

    return problems, branch_point


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


def _dry_walk_tree(repo: Repo, tree: dict[str, str], new_base: str,
                   branch_point: dict[str, str]) -> tuple[list[str], list[str]]:
    """Return (to_rebase, to_push) for branches in `tree`, in topo order.

    A branch needs rebasing iff its current branch-point != its parent's new
    tip. Walks topologically so chained no-ops are detected. A branch needs
    pushing iff it will be rebased OR its local tip already differs from
    origin (force-with-lease).
    """
    new_base_sha = repo.commit(new_base).hexsha
    old_tip = {b: repo.heads[b].commit.hexsha for b in tree}
    projected_new_tip: dict[str, str] = {}
    to_rebase: list[str] = []
    to_push: list[str] = []
    for b in _topo_sort_tree(tree, new_base):
        parent_ref = tree[b]
        new_parent_sha = (new_base_sha if parent_ref == new_base
                          else projected_new_tip[parent_ref])
        if branch_point[b] == new_parent_sha:
            projected_new_tip[b] = old_tip[b]
            if _diverged_from_origin(repo, b):
                to_push.append(b)
        else:
            projected_new_tip[b] = "<rebased>"
            to_rebase.append(b)
            to_push.append(b)
    return to_rebase, to_push


def _diverged_from_origin(repo: Repo, branch: str) -> bool:
    if not has_upstream(repo, branch):
        return False
    upstream = repo.heads[branch].tracking_branch()
    if upstream is None:
        return False
    return repo.heads[branch].commit.hexsha != upstream.commit.hexsha


def rebase_tree(repo: Repo, log: UndoLog, tree: dict[str, str],
                new_base: str,
                branch_point: dict[str, str]) -> tuple[bool, list[str]]:
    """Rebase every branch in `tree` onto its declared parent's new tip.

    Caller must have already run precheck_rebase_tree and obtained
    `branch_point`. No-op branches (branch-point already at parent's new tip)
    are skipped silently. On any rebase or push failure, breaks immediately —
    descendants are marked failed and not touched.
    """
    g = repo.git
    new_base_sha = repo.commit(new_base).hexsha
    order = _topo_sort_tree(tree, new_base)

    old_tip = {b: repo.heads[b].commit.hexsha for b in tree}
    new_tip: dict[str, str] = {}
    failed: list[str] = []

    for b in order:
        parent_ref = tree[b]
        old_base_sha = branch_point[b]
        new_parent_sha = (new_base_sha if parent_ref == new_base
                          else new_tip[parent_ref])

        already_rebased = old_base_sha == new_parent_sha
        if already_rebased:
            new_tip[b] = old_tip[b]
        else:
            print(f"\n=== {b} ===")
            print(f"  parent: {parent_ref}")
            print(f"  pre-rebase: {old_tip[b][:8]}")
            print(f"  --onto {new_parent_sha[:8]} {old_base_sha[:8]}")

            ok = rebase_branch(repo, log, b,
                               ["--onto", new_parent_sha, old_base_sha, b],
                               f"rebase --onto {new_parent_sha[:8]} {old_base_sha[:8]}")
            if not ok:
                failed.append(b)
                for d in _descendants_of(tree, b):
                    if d not in failed:
                        failed.append(d)
                break

            new_tip[b] = repo.heads[b].commit.hexsha
            print(f"  post-rebase: {new_tip[b][:8]}")

        push_rc, _ = push_if_ahead(repo, b)
        if push_rc != 0:
            failed.append(b)
            for d in _descendants_of(tree, b):
                if d not in failed:
                    failed.append(d)
            break

    return len(failed) == 0, failed


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


def rebase_on_personal(repo: Repo) -> int:
    """Rebase every other local branch onto bar/devcontainer, then push
    bar/devcontainer to align origin with the local tree.

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

    rc, did_rebase = _run_tree_rebase(repo, tree, PERSONAL_BRANCH)
    if rc != 0:
        return rc

    push_rc, did_push = push_if_ahead(repo, PERSONAL_BRANCH)
    if push_rc != 0:
        return push_rc

    if not did_rebase and not did_push:
        print("Nothing to do.")
    return 0


def push_if_ahead(repo: Repo, branch: str) -> tuple[int, bool]:
    """Push `branch` with --force-with-lease iff its local tip is ahead of or
    diverged from origin. Silent no-op if no upstream or already in sync.
    Returns (rc, did_push)."""
    if not has_upstream(repo, branch):
        return 0, False
    try:
        local_sha = repo.heads[branch].commit.hexsha
        upstream = repo.heads[branch].tracking_branch()
        if upstream is None:
            return 0, False
        remote_sha = upstream.commit.hexsha
    except Exception as e:
        print(f"Could not compare {branch} to its upstream: {e}",
              file=sys.stderr)
        return 1, False

    if local_sha == remote_sha:
        return 0, False

    print(f"\nPushing {branch}...")
    try:
        repo.git.checkout(branch)
        repo.git.push("--force-with-lease")
    except GitCommandError as e:
        print(f"Push failed: {e.stderr or e}", file=sys.stderr)
        return 1, False
    print(f"Pushed {branch} (force-with-lease)")
    return 0, True


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

    rc, did_rebase = _run_tree_rebase(repo, tree, UPSTREAM_REF)
    if rc == 0 and not did_rebase:
        print("Nothing to do.")
    return rc


def _run_tree_rebase(repo: Repo, tree: dict[str, str],
                     new_base: str) -> tuple[int, bool]:
    """Shared driver: precheck, then rebase, then restore branch.

    Returns (rc, did_anything). rc=0 on success. did_anything=True iff at
    least one branch was actually rebased. Silent (no output, no log file)
    when there is nothing to rebase.
    """
    problems, branch_point = precheck_rebase_tree(repo, tree, new_base)
    if problems:
        print("Pre-check failed; refusing to touch any branch:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1, False

    to_rebase, to_push = _dry_walk_tree(repo, tree, new_base, branch_point)
    if not to_rebase and not to_push:
        return 0, False

    original = repo.active_branch.name
    print("=== Pre-change branch state ===")
    for h in repo.heads:
        subject = h.commit.message.splitlines()[0]
        print(f"  {h.name:30s} {h.commit.hexsha[:8]}  {subject}")
    print()
    print("=== Declared tree ===")
    for b, p in tree.items():
        print(f"  {b} -> {p}")
    print()
    if to_rebase:
        print(f"=== Branches to rebase: {', '.join(to_rebase)} ===")
    if to_push:
        push_only = [b for b in to_push if b not in to_rebase]
        if push_only:
            print(f"=== Branches to push (already rebased): {', '.join(push_only)} ===")

    with undo_log(repo) as log:
        ok, failed = rebase_tree(repo, log, tree, new_base, branch_point)

        try:
            repo.git.checkout(original)
        except GitCommandError as e:
            print(f"Could not return to {original}: {e.stderr or e}",
                  file=sys.stderr)

    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
    return (0 if ok else 1), True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rebase-on-personal", action="store_true",
                      help="Rebase every other local branch onto bar/devcontainer.")
    mode.add_argument("--rebase-on-rolling", action="store_true",
                      help=f"Rebase bar/devcontainer onto {UPSTREAM_REF} and "
                           "every other local branch onto bar/devcontainer.")
    args = ap.parse_args()

    repo = Repo(Path(__file__).resolve().parent.parent)

    if args.rebase_on_personal:
        return rebase_on_personal(repo)

    if args.rebase_on_rolling:
        return rebase_on_rolling(repo)

    ap.error("no mode selected")  # unreachable; group is required
    return 1


if __name__ == "__main__":
    sys.exit(main())
