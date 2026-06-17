# .devcontainer scripts

- `Dockerfile` — image definition.
- `compose.yaml` — base docker-compose service (`dev`). Holds mounts, env, caps, network/pid/ipc, named volumes.
- `compose.generated.yaml` — **auto-generated, gitignored**. Written by `host-setup.sh` pre-build with `include:` entries for enabled plugins that have a `compose.yaml`.
- `devcontainer.json` — VS Code Dev Containers config. Points `dockerComposeFile` at both compose files.
- `plugins.sh` — sourced shared file with the `PLUGINS=(...)` array. **Single source of truth for which plugins are enabled.**
- `on-create-command.sh` — runs once inside the container when it's first created.
- `post-create-command.sh` — runs inside the container after creation. Sources `plugins.sh`, loops over enabled plugins and runs each one's `in-container.sh`.
- `update-content-command.sh` — runs inside the container on content updates.
- `host-setup.sh` — **runs on the host** as `initializeCommand` (pre-build). Idempotent. Generates `compose.generated.yaml`, then handles ssh-agent, perf sysctls, `docker cp` of host-only files, and sources each enabled plugin's `on-host.sh`.

## Plugins

A plugin is a folder under `plugins/` with up to three files, all optional:

- `compose.yaml` — extra mounts/env/caps merged into the `dev` service by docker compose.
- `in-container.sh` — executable; run from `post-create-command.sh`.
- `on-host.sh` — **sourced** from `host-setup.sh`; can call `copy_if_changed` and use `$CONTAINER`.

### Enable / disable

Edit the `PLUGINS=(...)` array in `plugins.sh` — add a name to enable, remove or comment to disable. Then rebuild the container in VS Code so `compose.generated.yaml` is regenerated and picked up.
