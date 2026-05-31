#!/bin/bash
set -eo pipefail

[ -f /.dockerenv ] || { echo "ERROR: $0 must run inside the devcontainer, not on the host" >&2; exit 1; }
[ -n "$OVERLAY_WS" ] || { echo "ERROR: \$OVERLAY_WS unset — devcontainer not initialized" >&2; exit 1; }

# Enable autocomplete for user
cp /etc/skel/.bashrc ~/

# Source overlay workspace for interactive use
echo 'source "$OVERLAY_WS/install/setup.bash"' >> ~/.bashrc

# Run in-container hook for each enabled plugin (in-container.sh or .py)
HERE="$(cd "$(dirname "$0")" && pwd)"
for plugin in $("$HERE/list-enabled-plugins.py"); do
    for hook in "$HERE/plugins/$plugin"/in-container.{sh,py}; do
        if [ -x "$hook" ]; then
            echo "plugin $plugin: running $(basename "$hook")"
            "$hook"
        fi
    done
done
