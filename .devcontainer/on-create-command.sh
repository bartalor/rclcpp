#!/bin/bash
set -eo pipefail

[ -f /.dockerenv ] || { echo "ERROR: $0 must run inside the devcontainer, not on the host" >&2; exit 1; }
[ -n "$OVERLAY_WS" ] || { echo "ERROR: \$OVERLAY_WS unset — devcontainer not initialized" >&2; exit 1; }
[ -n "$ROS_DISTRO" ] || { echo "ERROR: \$ROS_DISTRO unset — devcontainer not initialized" >&2; exit 1; }

git config --global --add safe.directory "*"

# import pinned source overlays (see overlay.repos for rationale)
. /opt/ros/$ROS_DISTRO/setup.sh
sudo apt-get update
sudo apt-get install -y python3-vcstool
sudo install -d -o ubuntu -g ubuntu $OVERLAY_WS/src
vcs import --input .devcontainer/overlay.repos $OVERLAY_WS/src

# on-create runs on a fresh container — drop any stale build/install from the
# named overlay volume so CMake caches can't pin packages (e.g. rcl_DIR) to
# /opt/ros/$ROS_DISTRO from before the source overlay existed.
rm -rf $OVERLAY_WS/build $OVERLAY_WS/install $OVERLAY_WS/log

# install overlay deps from mounted source
rosdep update --rosdistro=$ROS_DISTRO
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
