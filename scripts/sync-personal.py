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


def _has_merge_commit(repo: Repo, base: str, tip: str) -> bool:
    return any(len(c.parents) > 1 for c in repo.iter_commits(f"{base}..{tip}"))


def build_branch_tree(repo: Repo,
                      new_base: str) -> dict[str, str]:
    """Return the explicit branch tree by repo convention.

    Convention (per CLAUDE.md):
      - bar/devcontainer is rooted on new_base (upstream/rolling).
      - Every other local branch is stacked on bar/devcontainer.
      - The new_base ref itself (if it shows up as a local branch) is excluded.

    Returns {branch_name: parent_ref}, where parent_ref is either another
    branch name in the dict or `new_base`.
    """
    tree: dict[str, str] = {}
    local_names = {h.name for h in repo.heads}
    if PERSONAL_BRANCH not in local_names:
        return tree
    tree[PERSONAL_BRANCH] = new_base
    for h in repo.heads:
        name = h.name
        if name == PERSONAL_BRANCH:
            continue
        if name == UPSTREAM_BRANCH:
            continue
        tree[name] = PERSONAL_BRANCH
    return tree


def precheck_rebase_tree(repo: Repo, tree: dict[str, str],
                         new_base: str) -> list[str]:
    """Validate that the declared `tree` is rebase-safe.

    Returns a list of problems. Empty list = safe to proceed. Non-empty =
    abort, no mutations.

    Hard rule: every child's branch-point relative to its declared parent
    must equal its parent's CURRENT tip. If the parent has any commits past
    the branch-point, the child is stale — abort. The user must rebase the
    child onto the parent manually first. This is what guarantees that
    `git rebase --onto NEW_PARENT_TIP OLD_PARENT_TIP child` only replays
    the child's own commits.

    Other checks:
      - Every branch in `tree` exists locally.
      - new_base resolves.
      - No merge commits in (parent..child) ranges.
      - Every parent_ref is either new_base or another branch in `tree`.
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
            # cycle in declared tree; precheck should have caught upstream
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

    Pre-checks the entire tree first. Aborts before any side effect if any
    check fails. After each successful rebase, force-with-lease pushes the
    branch if it has an upstream. Returns (ok, failed_branch_names).
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
        else:
            print("  no upstream; skipping push")

    return len(failed) == 0, failed


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
    """Rebase bar/devcontainer + every other local branch onto upstream/rolling.

    Delegates the actual tree-aware rebase to rebase_tree, which pre-checks
    everything and aborts before touching anything if there's any doubt.
    """
    dirty = changed_paths(repo)
    if dirty:
        print("Refusing: working tree is not clean.", file=sys.stderr)
        for p in dirty:
            print(f"  {p}", file=sys.stderr)
        return 1

    g = repo.git
    original = repo.active_branch.name

    if PERSONAL_BRANCH not in [h.name for h in repo.heads]:
        print(f"Refusing: {PERSONAL_BRANCH} does not exist locally.", file=sys.stderr)
        return 1

    print(f"Fetching {UPSTREAM_REF}...")
    try:
        g.fetch(UPSTREAM_REMOTE, UPSTREAM_BRANCH)
    except GitCommandError as e:
        print(f"Fetch failed: {e.stderr or e}", file=sys.stderr)
        return 1

    tree = build_branch_tree(repo, UPSTREAM_REF)
    if not tree:
        print(f"No branches to rebase ({PERSONAL_BRANCH} missing).", file=sys.stderr)
        return 1

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

    ok, failed = rebase_tree(repo, log_fh, tree, UPSTREAM_REF)

    try:
        g.checkout(original)
    except GitCommandError as e:
        print(f"Could not return to {original}: {e.stderr or e}", file=sys.stderr)

    log_fh.close()
    print(f"\nUndo log written: {log_path}")

    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
    return 0 if ok else 1


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
