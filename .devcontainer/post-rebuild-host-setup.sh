#!/bin/bash
# Run on the host after a devcontainer rebuild to copy host-only files
# into the container. Idempotent: skips files that already match.
set -eo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

CONTAINER=$(docker ps \
    --filter "label=devcontainer.local_folder=$REPO_ROOT" \
    --format "{{.ID}}" \
    | head -n1)

if [ -z "$CONTAINER" ]; then
    echo "no running devcontainer for $REPO_ROOT" >&2
    exit 1
fi
echo "container: $CONTAINER"

copy_if_changed() {
    local src=$1 dst=$2
    if [ ! -e "$src" ]; then
        echo "skip $src (missing)"
        return
    fi
    local src_sum dst_sum
    src_sum=$(sha256sum "$src" | awk '{print $1}')
    dst_sum=$(docker exec "$CONTAINER" sha256sum "$dst" 2>/dev/null | awk '{print $1}' || true)
    if [ "$src_sum" = "$dst_sum" ]; then
        echo "ok   $dst"
        return
    fi
    docker cp "$src" "$CONTAINER:$dst"
    echo "copy $src -> $dst"
}

copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/git-Pretty" /usr/local/bin/git-Pretty
copy_if_changed "$HOME/dotfiles/bash/.bashrc.d/git-completions.sh" /etc/bash_completion.d/git-completions.sh
