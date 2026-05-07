#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

# install overlay deps from mounted source
. /opt/ros/$ROS_DISTRO/setup.sh
rosdep update --rosdistro=$ROS_DISTRO
sudo apt-get update
sudo rosdep install -q -y \
    --from-paths $OVERLAY_WS/src \
    --ignore-src \
    --dependency-types=build \
    --dependency-types=buildtool \
    --dependency-types=build_export \
    --dependency-types=buildtool_export \
    --dependency-types=exec \
    --dependency-types=test

.devcontainer/update-content-command.sh
