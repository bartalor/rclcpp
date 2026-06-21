# Shared list of enabled plugins. Sourced by initialize-command.sh,
# post-create-command.sh, and post-start-command.sh. Edit the array to enable/disable plugins;
# a rebuild is needed for plugins that contribute a compose.yaml.
PLUGINS=(
    mcp-cpp
    open-source-utils
    git-graph-2
    bench-1949
)
