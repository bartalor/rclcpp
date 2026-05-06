#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

# install overlay deps from mounted source
. /opt/ros/$ROS_DISTRO/setup.sh
apt-get update
rosdep install -q -y \
    --from-paths $OVERLAY_WS/src \
    --ignore-src
rm -rf /var/lib/apt/lists/*

.devcontainer/update-content-command.sh
