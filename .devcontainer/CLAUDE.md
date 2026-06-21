# .devcontainer scripts

- `Dockerfile` — image definition.
- `compose.yaml` — base docker-compose service (`dev`). Holds mounts, env, caps, network/pid/ipc, named volumes.
- `compose.generated.yaml` — **auto-generated, gitignored**. Written by `initialize-command.sh` pre-build with `include:` entries for enabled plugins that have a `compose.yaml`.
- `devcontainer.json` — VS Code Dev Containers config. Points `dockerComposeFile` at both compose files.
- `plugins.sh` — sourced shared file with the `PLUGINS=(...)` array. **Single source of truth for which plugins are enabled.**

Top-level scripts match the devcontainer hook names:

- `initialize-command.sh` — **runs on the host** as `initializeCommand` (pre-build/start). Idempotent. Generates `compose.generated.yaml`, then handles ssh-agent, perf sysctls, `docker cp` of host-only files, and sources each enabled plugin's `initialize-command.sh`.
- `on-create-command.sh` — runs once inside the container when it's first created (`onCreateCommand`).
- `update-content-command.sh` — runs inside the container on content updates (`updateContentCommand`).
- `post-create-command.sh` — runs inside the container after creation (`postCreateCommand`). Sources `plugins.sh`, loops over enabled plugins and runs each one's `post-create-command.sh`.
- `post-start-command.sh` — runs inside the container on every start (`postStartCommand`). Sources `plugins.sh`, loops over enabled plugins and runs each one's `post-start-command.sh`.

## Plugins

A plugin is a folder under `plugins/` with up to four files, all optional:

- `compose.yaml` — extra mounts/env/caps merged into the `dev` service by docker compose.
- `initialize-command.sh` — **sourced** from `initialize-command.sh`; runs on the host; can call `copy_if_changed` and use `$CONTAINER`.
- `post-create-command.sh` (or `.py`) — executable; run from `post-create-command.sh` on container creation.
- `post-start-command.sh` (or `.py`) — executable; run from `post-start-command.sh` on every container start.

### Enable / disable

Edit the `PLUGINS=(...)` array in `plugins.sh` — add a name to enable, remove or comment to disable. Then rebuild the container in VS Code so `compose.generated.yaml` is regenerated and picked up.
