#!/bin/bash
# Run each disabled plugin's uninstall.sh, if present. A plugin is "disabled"
# when its folder exists under plugins/ but its name is NOT in the PLUGINS
# array in plugins.sh. Invoke manually after editing plugins.sh.
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
# shellcheck source=plugins.sh
. "$HERE/plugins.sh"

is_enabled() {
    local name=$1
    for p in "${PLUGINS[@]}"; do
        [ "$p" = "$name" ] && return 0
    done
    return 1
}

for dir in "$HERE/plugins"/*/; do
    name=$(basename "$dir")
    is_enabled "$name" && continue
    hook="$dir/uninstall.sh"
    [ -f "$hook" ] || continue
    echo "plugin $name: running uninstall.sh"
    # shellcheck source=/dev/null
    . "$hook"
done
