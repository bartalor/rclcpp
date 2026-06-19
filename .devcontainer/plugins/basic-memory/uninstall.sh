# Remove the symlinks installed by on-host.sh and drop their entries from
# .git/info/exclude. Sourced by uninstall-disabled-plugins.sh with
# $REPO_ROOT set.

SRC_DIR="$REPO_ROOT/.devcontainer/plugins/basic-memory/skills"
DST_DIR="$REPO_ROOT/.claude/skills"
EXCLUDE="$REPO_ROOT/.git/info/exclude"

for src in "$SRC_DIR"/*; do
    name=$(basename "$src")
    dst="$DST_DIR/$name"
    if [ -L "$dst" ]; then
        rm "$dst"
        echo "plugin basic-memory: removed .claude/skills/$name"
    fi
done

if [ -f "$EXCLUDE" ]; then
    tmp=$(mktemp)
    grep -v '^\.claude/skills/basic-memory-' "$EXCLUDE" > "$tmp" || true
    mv "$tmp" "$EXCLUDE"
fi
