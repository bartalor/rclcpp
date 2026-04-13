#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

.devcontainer/update-content-command.sh
