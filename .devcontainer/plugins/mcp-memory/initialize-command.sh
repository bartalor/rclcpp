#!/bin/bash
# Host-side setup for the mcp-memory plugin. Sourced by initialize-command.sh
# with copy_if_changed() and $CONTAINER already defined.
set -eo pipefail

copy_if_changed "$HOME/.mcp-memory/.env" /home/ubuntu/.mcp-memory/.env
