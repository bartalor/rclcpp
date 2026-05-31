#!/bin/bash
# Host-side setup for the devcontainer. Safe to re-run any time: every step
# is idempotent and checks before acting. Run after a rebuild, after a host
# reboot, or whenever something feels off.
set -eo pipefail

[ ! -f /.dockerenv ] || { echo "ERROR: $0 must run on the host, not inside the container" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Make sure the host SSH agent has a key loaded so the forwarded socket is
# usable from inside the container (git fetch of SSH remotes, etc.).
if ! ssh-add -l >/dev/null 2>&1; then
    ssh-add "$HOME/.ssh/id_ed25519"
    echo "ssh-add: loaded $HOME/.ssh/id_ed25519 into host agent"
fi

# Allow unprivileged perf profiling (kernel + user) so `perf record` works
# inside the container. Resets on reboot, so we re-apply here.
if [ "$(cat /proc/sys/kernel/perf_event_paranoid)" -gt 1 ]; then
    sudo sysctl -q kernel.perf_event_paranoid=1
    echo "sysctl: kernel.perf_event_paranoid=1"
fi

# Expose kernel symbol addresses so `perf report` resolves kernel frames
# instead of showing raw 0xffffffff... hex. Resets on reboot.
if [ "$(cat /proc/sys/kernel/kptr_restrict)" -ne 0 ]; then
    sudo sysctl -q kernel.kptr_restrict=0
    echo "sysctl: kernel.kptr_restrict=0"
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
    docker exec "$CONTAINER" mkdir -p "$(dirname "$dst")"
    docker cp "$src" "$CONTAINER:$dst"
    echo "copy $src -> $CONTAINER:$dst"
}

copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/git-Pretty" /usr/local/bin/git-Pretty
copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/ram-cleanup" /usr/local/bin/ram-cleanup
copy_if_changed "$HOME/dotfiles/bash/.bashrc.d/git-completions.sh" /etc/bash_completion.d/git-completions.sh
copy_if_changed "$HOME/.netrc" /home/ubuntu/.netrc
copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/claude-mcp-toggle" /usr/local/bin/claude-mcp-toggle

# Run on-host hook for each enabled plugin (sourced so it sees copy_if_changed + $CONTAINER)
HERE="$(cd "$(dirname "$0")" && pwd)"
for plugin in $("$HERE/list-enabled-plugins.py"); do
    hook="$HERE/plugins/$plugin/on-host.sh"
    if [ -f "$hook" ]; then
        echo "plugin $plugin: running on-host.sh"
        # shellcheck source=/dev/null
        . "$hook"
    fi
done
