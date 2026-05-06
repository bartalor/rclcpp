#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

# install overlay deps from mounted source
. /opt/ros/$ROS_DISTRO/setup.sh
rosdep update
apt-get update
rosdep install -q -y \
    --from-paths $OVERLAY_WS/src \
    --ignore-src

.devcontainer/update-content-command.sh
