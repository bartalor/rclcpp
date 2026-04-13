#!/bin/bash
set -eo pipefail

# Enable autocomplete for user
cp /etc/skel/.bashrc ~/

# Source overlay workspace for interactive use
echo 'source "$OVERLAY_WS/install/setup.bash"' >> ~/.bashrc
