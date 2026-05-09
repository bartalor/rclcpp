# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `scripts/`, `CLAUDE.md`, etc. **Always create feature branches off `bar/devcontainer`**, never off `upstream/rolling`. The branch keeps the personal files; only the upstream PR excludes them.

`scripts/sync-personal.py` has three mutually-exclusive modes; all precheck everything and abort on any problem before mutating anything. The script's `PERSONAL_PATHS` list is the source of truth for what counts as personal.

- `python3 scripts/sync-personal.py --commit-personal -m "..."` — commit dirty personal files on `bar/devcontainer`, push, checkout back to the original branch. Refuses if non-personal files are dirty or if no personal files have changed.
- `python3 scripts/sync-personal.py --rebase-on-personal` — rebase every other local branch onto `bar/devcontainer` (tree-aware, no duplicate commits). Refuses on a dirty tree.
- `python3 scripts/sync-personal.py --rebase-on-rolling` — fetch `upstream/rolling`, rebase `bar/devcontainer` onto it, then rebase every other local branch onto `bar/devcontainer`'s new tip (tree-aware). Refuses on a dirty tree or any stale branch.

# Persistence

Every fix must survive `docker rmi` + rebuild. Container-side fixes → Dockerfile / lifecycle scripts on `bar/devcontainer`. Host-side setup → `.devcontainer/post-rebuild-host-setup.sh`.

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.
