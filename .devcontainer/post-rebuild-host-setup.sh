#!/bin/bash
# Host-side setup for the devcontainer. Safe to re-run any time: every step
# is idempotent and checks before acting. Run after a rebuild, after a host
# reboot, or whenever something feels off.
set -eo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Make sure the host SSH agent has a key loaded so the forwarded socket is
# usable from inside the container (git fetch of SSH remotes, etc.).
if ! ssh-add -l >/dev/null 2>&1; then
    ssh-add "$HOME/.ssh/id_ed25519"
    echo "ssh-add: loaded $HOME/.ssh/id_ed25519 into host agent"
fi

CONTAINER=$(docker ps \
    --filter "label=devcontainer.local_folder=$REPO_ROOT" \
    --format "{{.ID}}" \
    | head -n1)

if [ -z "$CONTAINER" ]; then
    echo "no running devcontainer for $REPO_ROOT, skipping in-container steps"
    exit 0
fi

copy_if_changed() {
    local src=$1 dst=$2
    if [ ! -e "$src" ]; then
        echo "skip $dst: source $src missing"
        return
    fi
    local src_sum dst_sum
    src_sum=$(sha256sum "$src" | awk '{print $1}')
    dst_sum=$(docker exec "$CONTAINER" sha256sum "$dst" 2>/dev/null | awk '{print $1}' || true)
    if [ "$src_sum" = "$dst_sum" ]; then
        return
    fi
    docker cp "$src" "$CONTAINER:$dst"
    echo "copy $src -> $CONTAINER:$dst"
}

copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/git-Pretty" /usr/local/bin/git-Pretty
copy_if_changed "$HOME/dotfiles/bash/.bashrc.d/git-completions.sh" /etc/bash_completion.d/git-completions.sh
