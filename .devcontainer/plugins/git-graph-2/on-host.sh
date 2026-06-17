# Copy the host's sideloaded Git Graph 2 fork (hansu.git-graph-2, not on the
# marketplace) into the container's VS Code Server extensions dir and register
# it in extensions.json. Sourced by host-setup.sh with $CONTAINER set.

SRC=$(ls -d "$HOME"/.vscode/extensions/hansu.git-graph-2-* 2>/dev/null | sort -V | tail -n1)
if [ -z "$SRC" ]; then
    echo "plugin git-graph-2: host extension not found under ~/.vscode/extensions, skipping"
    return 0
fi

REL=$(basename "$SRC")
DST_DIR=/home/ubuntu/.vscode-server/extensions
DST=$DST_DIR/$REL

if docker exec "$CONTAINER" test -d "$DST"; then
    echo "plugin git-graph-2: $REL already present in container"
else
    docker exec -u ubuntu "$CONTAINER" mkdir -p "$DST_DIR"
    docker cp "$SRC" "$CONTAINER:$DST"
    docker exec "$CONTAINER" chown -R ubuntu:ubuntu "$DST"
    echo "plugin git-graph-2: copied $REL into container"
fi

VERSION=${REL#hansu.git-graph-2-}
docker exec -i -u ubuntu "$CONTAINER" python3 - "$REL" "$VERSION" <<'PY'
import json, os, sys, pathlib
rel, version = sys.argv[1], sys.argv[2]
p = pathlib.Path("/home/ubuntu/.vscode-server/extensions/extensions.json")
p.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(p.read_text()) if p.exists() else []
entry = {
    "identifier": {"id": "hansu.git-graph-2"},
    "version": version,
    "location": {"$mid": 1, "path": f"/home/ubuntu/.vscode-server/extensions/{rel}", "scheme": "file"},
    "relativeLocation": rel,
    "metadata": {"installedTimestamp": 0, "pinned": True, "source": "vsix"},
}
existing = next((e for e in data if e.get("identifier", {}).get("id") == "hansu.git-graph-2"), None)
if existing == entry:
    sys.exit(0)
if existing:
    data.remove(existing)
data.append(entry)
p.write_text(json.dumps(data, indent=2))
print(f"plugin git-graph-2: registered {rel} in extensions.json")
PY
