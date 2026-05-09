# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `scripts/`, `CLAUDE.md`, etc. **Always create feature branches off `bar/devcontainer`**, never off `upstream/rolling`. The branch keeps the personal files; only the upstream PR excludes them.

To commit personal-file changes: switch to `bar/devcontainer`, commit and push there, then switch back and run `--rebase-on-personal` to fan the new tip out to feature branches.

`scripts/rebase-branches.py` has two mutually-exclusive modes; both precheck everything and abort on any problem before mutating anything.

- `python3 scripts/rebase-branches.py --rebase-on-personal` — rebase every other local branch onto `bar/devcontainer` (tree-aware, no duplicate commits). Refuses on a dirty tree.
- `python3 scripts/rebase-branches.py --rebase-on-rolling` — fetch `upstream/rolling`, rebase `bar/devcontainer` onto it, then rebase every other local branch onto `bar/devcontainer`'s new tip (tree-aware). Refuses on a dirty tree or any stale branch.

# Persistence

Every fix must survive `docker rmi` + rebuild. Container-side fixes → Dockerfile / lifecycle scripts on `bar/devcontainer`. Host-side setup → `.devcontainer/post-rebuild-host-setup.sh`.

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.
