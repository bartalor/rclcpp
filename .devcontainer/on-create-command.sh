#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

# install overlay deps from mounted source
. /opt/ros/$ROS_DISTRO/setup.sh
rosdep update
apt-get update
rosdep install -q -y \
    --from-paths $OVERLAY_WS/src \
    --ignore-src \
    --dependency-types=build \
    --dependency-types=buildtool \
    --dependency-types=build_export \
    --dependency-types=buildtool_export \
    --dependency-types=exec

.devcontainer/update-content-command.sh

# expose source under the host's path so tooling (eg. claude) keys the
# project the same way inside and outside the container
mkdir -p "$(dirname "$HOST_WORKSPACE_FOLDER")"
ln -sfn "$OVERLAY_WS/src/rclcpp" "$HOST_WORKSPACE_FOLDER"
