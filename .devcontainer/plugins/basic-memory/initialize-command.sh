# Symlink this plugin's skills into .claude/skills/ and exclude the link
# names from git. Sourced by initialize-command.sh with $REPO_ROOT set.

SRC_DIR="$REPO_ROOT/.devcontainer/plugins/basic-memory/skills"
DST_DIR="$REPO_ROOT/.claude/skills"
EXCLUDE="$REPO_ROOT/.git/info/exclude"

mkdir -p "$DST_DIR"

for src in "$SRC_DIR"/*; do
    name=$(basename "$src")
    dst="$DST_DIR/$name"
    target=$(realpath --relative-to="$DST_DIR" "$src")
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$target" ]; then
        continue
    fi
    rm -rf "$dst"
    ln -s "$target" "$dst"
    echo "plugin basic-memory: linked .claude/skills/$name"
done

for src in "$SRC_DIR"/*; do
    line=".claude/skills/$(basename "$src")"
    grep -qxF "$line" "$EXCLUDE" 2>/dev/null || echo "$line" >> "$EXCLUDE"
done
