#!/bin/bash
# Host-side setup for the mcp-memory plugin. Sourced by post-rebuild-host-setup.sh
# with copy_if_changed() and $CONTAINER already defined.
set -eo pipefail

copy_if_changed "$HOME/dotfiles/path_scripts/.local/bin/claude-mcp-toggle" /usr/local/bin/claude-mcp-toggle
copy_if_changed "$HOME/.mcp-memory/.env" /home/ubuntu/.mcp-memory/.env
