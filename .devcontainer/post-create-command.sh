#!/bin/bash
set -eo pipefail

[ -f /.dockerenv ] || { echo "ERROR: $0 must run inside the devcontainer, not on the host" >&2; exit 1; }
[ -n "$OVERLAY_WS" ] || { echo "ERROR: \$OVERLAY_WS unset — devcontainer not initialized" >&2; exit 1; }

# Enable autocomplete for user
cp /etc/skel/.bashrc ~/

# Source overlay workspace for interactive use
echo 'source "$OVERLAY_WS/install/setup.bash"' >> ~/.bashrc

# Wire repo-tracked git hooks
git -C "$(cd "$(dirname "$0")/.." && pwd)" config core.hooksPath .githooks

# Run post-create hook for each enabled plugin (post-create-command.sh or .py)
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=plugins.sh
. "$HERE/plugins.sh"
for plugin in "${PLUGINS[@]}"; do
    for hook in "$HERE/plugins/$plugin"/post-create-command.{sh,py}; do
        if [ -x "$hook" ]; then
            echo "plugin $plugin: running $(basename "$hook")"
            "$hook"
        fi
    done
done
