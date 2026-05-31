# .devcontainer scripts

- `Dockerfile` — image definition.
- `compose.yaml` — base docker-compose service (`dev`). Holds mounts, env, caps, network/pid/ipc, named volumes. Also has an `include:` list of plugin compose files — **this is where plugins are enabled/disabled**.
- `devcontainer.json` — VS Code Dev Containers config. References `compose.yaml` only; plugin wiring lives in `compose.yaml`'s `include:`.
- `on-create-command.sh` — runs once inside the container when it's first created.
- `post-create-command.sh` — runs inside the container after creation. Loops over enabled plugins and runs each one's `in-container.sh`.
- `update-content-command.sh` — runs inside the container on content updates.
- `post-rebuild-host-setup.sh` — **runs on the host** (not in the container). Idempotent, safe to re-run any time. Today: ssh-agent key load, perf sysctls, `docker cp` of host-only files. Also loops over enabled plugins and sources each one's `on-host.sh`.
- `list-enabled-plugins.py` — prints enabled plugin names by parsing `compose.yaml`'s `include:` list. Used by the two loops above.

## Plugins

A plugin is a folder under `plugins/` with up to three files, all optional:

- `compose.yaml` — extra mounts/env/caps merged into the `dev` service by docker compose.
- `in-container.sh` — executable; run from `post-create-command.sh`.
- `on-host.sh` — **sourced** from `post-rebuild-host-setup.sh`; can call `copy_if_changed` and use `$CONTAINER`.

### Enable / disable

The `include:` list in `compose.yaml` is the single source of truth. To disable a plugin: comment out its line. To re-enable: uncomment. Then rebuild the container in VS Code.

The script loops auto-skip plugins that aren't listed, so the mounts and the lifecycle hooks toggle together.
