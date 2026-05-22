# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `CLAUDE.md`, etc.

# Persistence

Every fix must survive `docker rmi` + rebuild. Container-side fixes → Dockerfile / lifecycle scripts on `bar/devcontainer`. Host-side setup → `.devcontainer/post-rebuild-host-setup.sh`.

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.
