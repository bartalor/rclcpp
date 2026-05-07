# .devcontainer scripts

- `Dockerfile` — image definition.
- `devcontainer.json` — VS Code Dev Containers config.
- `on-create-command.sh` — runs once inside the container when it's first created.
- `post-create-command.sh` — runs inside the container after creation.
- `update-content-command.sh` — runs inside the container on content updates.
- `post-rebuild-host-setup.sh` — **runs on the host** (not in the container). General-purpose host-side setup hook: anything that needs to happen on the host to make the container fully usable. Run after a container rebuild, after a host reboot, or any time something feels off. Every step must be idempotent — the script is meant to be safe to re-run any time. Today it ensures the host SSH agent has the key loaded (so the forwarded agent socket is usable from inside the container) and `docker cp`s host-only files in.
