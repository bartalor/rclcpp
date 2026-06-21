#!/bin/bash
set -eo pipefail

[ -f /.dockerenv ] || { echo "ERROR: $0 must run inside the devcontainer, not on the host" >&2; exit 1; }

# Run post-start hook for each enabled plugin (post-start-command.sh or .py)
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=plugins.sh
. "$HERE/plugins.sh"
for plugin in "${PLUGINS[@]}"; do
    for hook in "$HERE/plugins/$plugin"/post-start-command.{sh,py}; do
        if [ -x "$hook" ]; then
            echo "plugin $plugin: running $(basename "$hook")"
            "$hook"
        fi
    done
done
