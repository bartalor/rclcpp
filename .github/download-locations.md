# Build artifacts and other downloads

**Never invent a path or "convention" on the fly.** Before downloading anything (GHA artifacts, run logs, release tarballs, anything), ask the user where it should go. One pre-existing file in `/tmp/` is not a convention — it's one file. Do not generalize from it.

## Established locations

- **GHA run artifacts** (`gh run download <id>`): `/tmp/gha-artifact-<run-id>/`
- **GHA run logs** (`gh run view --log`): `/tmp/gh-cli-cache/run-log-<run-id>-*.zip` (gh's own cache dir)

If you need to download something not listed above, ask the user where it goes, then add the location here in the same commit.
