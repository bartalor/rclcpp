# Shared list of enabled plugins. Sourced by host-setup.sh and
# post-create-command.sh. Edit the array to enable/disable plugins;
# a rebuild is needed for plugins that contribute a compose.yaml.
PLUGINS=(
    basic-memory
    mcp-cpp
    open-source-utils
    git-graph-2
    # mcp-memory
)
