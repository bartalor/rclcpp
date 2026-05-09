# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `scripts/`, `CLAUDE.md`, etc. **Always create feature branches off `bar/devcontainer`**, never off `upstream/rolling`. The branch keeps the personal files; only the upstream PR excludes them.

Use `python3 scripts/sync-personal.py -m "..."` to sync personal-file edits made on a feature branch: it commits them on `bar/devcontainer`, pushes, then rebases the feature branch on top and pushes that too. The script's `PERSONAL_PATHS` list is the source of truth for what counts as personal.

Use `python3 scripts/sync-personal.py --rebase-on-rolling` to fetch `upstream/rolling` and rebase every local branch onto it independently, force-with-lease pushing each one that has an upstream. Refuses on a dirty working tree.

# Persistence

Every fix must survive `docker rmi` + rebuild. Container-side fixes → Dockerfile / lifecycle scripts on `bar/devcontainer`. Host-side setup → `.devcontainer/post-rebuild-host-setup.sh`.

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.
