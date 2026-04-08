#!/bin/bash
set -e

# Set up colcon workspace with symlink to rclcpp
sudo mkdir -p /home/ws/src
sudo chown -R "$(whoami)" /home/ws
ln -sfn "$HOME/src/rclcpp" /home/ws/src/rclcpp

# Install ROS 2 dependencies
# Skip test/benchmark deps not available as apt packages on rolling
rosdep update
cd /home/ws
rosdep install --from-paths src --ignore-src -y \
    --skip-keys "mimick_vendor performance_test_fixture ament_cmake_google_benchmark test_msgs"

# Build workspace
. /opt/ros/rolling/setup.sh
colcon build --symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
