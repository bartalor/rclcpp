# Branching

`bar/devcontainer` is the personal-preferences root: `.devcontainer/`, `.vscode/`, `CLAUDE.md`, etc. **Always create feature branches off `bar/devcontainer`**, never off `upstream/rolling`. The branch keeps the personal files; only the upstream PR excludes them.

# Persistence

Every fix must survive `docker rmi` + rebuild. Container-side fixes → Dockerfile / lifecycle scripts on `bar/devcontainer`. Host-side setup → `.devcontainer/post-rebuild-host-setup.sh`.

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).
