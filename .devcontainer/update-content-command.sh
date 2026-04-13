#!/bin/bash
set -eo pipefail

WS="/home/ws"
cd "$WS"

colcon cache lock

BUILD_UNFINISHED=$(
    colcon list \
        --names-only \
        --packages-select rclcpp \
        --packages-skip-build-finished \
    | xargs)
echo "BUILD_UNFINISHED: $BUILD_UNFINISHED"

BUILD_FAILED=$(
    colcon list \
        --names-only \
        --packages-select rclcpp \
        --packages-select-build-failed \
    | xargs)
echo "BUILD_FAILED: $BUILD_FAILED"

BUILD_INVALID=$(
    colcon list \
        --names-only \
        --packages-select rclcpp \
        --packages-select-cache-invalid \
        --packages-select-cache-key build \
    | xargs)
echo "BUILD_INVALID: $BUILD_INVALID"

BUILD_PACKAGES=""
if [ -n "$BUILD_UNFINISHED" ] || \
    [ -n "$BUILD_FAILED" ] || \
    [ -n "$BUILD_INVALID" ]
then
    BUILD_PACKAGES="rclcpp"
fi
echo "BUILD_PACKAGES: $BUILD_PACKAGES"

if [ -n "$BUILD_PACKAGES" ]; then
    . /opt/ros/rolling/setup.sh
    colcon build \
        --symlink-install \
        --mixin release ccache compile-commands lld \
        --packages-select ${BUILD_PACKAGES}
fi
