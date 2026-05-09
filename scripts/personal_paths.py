"""Path classification shared between sync-personal.py and build-upstream-branch.py.

Two sets:

  PERSONAL_BRANCH_PATHS
    Paths that live on bar/devcontainer (the personal-preferences root).

  PR_EXCLUDED_PATHS
    Superset of the above plus paths that are not on bar/devcontainer but
    must still be kept out of upstream PRs (e.g. PR_DESCRIPTION.md, drafted
    locally).

A path "matches" an entry if the entry is the path itself or a directory
prefix of it (entry ends with '/').
"""

from typing import Iterable

PERSONAL_BRANCH_PATHS: tuple[str, ...] = (
    ".devcontainer/",
    ".vscode/",
    "scripts/",
    ".claude/",
    "CLAUDE.md",
    "renovate.json",
)

PR_EXCLUDED_PATHS: tuple[str, ...] = PERSONAL_BRANCH_PATHS + (
    "PR_DESCRIPTION.md",
)


def path_matches(path: str, patterns: Iterable[str]) -> bool:
    for p in patterns:
        if p.endswith("/"):
            if path.startswith(p):
                return True
        elif path == p:
            return True
    return False


def classify_paths(paths: Iterable[str],
                   excluded: Iterable[str]) -> str:
    """Classify a set of paths against `excluded`.

    Returns:
      "empty"    — no paths
      "personal" — every path matches `excluded`
      "upstream" — no path matches `excluded`
      "mixed"    — some do, some don't
    """
    paths = list(paths)
    if not paths:
        return "empty"
    excluded = tuple(excluded)
    hits = [path_matches(p, excluded) for p in paths]
    if all(hits):
        return "personal"
    if not any(hits):
        return "upstream"
    return "mixed"
