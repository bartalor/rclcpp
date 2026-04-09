#!/bin/bash
set -e

# Set up colcon workspace
sudo chown -R "$(whoami)" /home/ws
cd /home/ws

# Clone ROS 2 repos (rclcpp already mounted, --skip-existing skips it)
vcs import --input https://raw.githubusercontent.com/ros2/ros2/rolling/ros2.repos --skip-existing src

# Install system dependencies
sudo apt-get update
rosdep update
rosdep install --from-paths src --ignore-src -y

# Build rclcpp and its dependencies only
. /opt/ros/rolling/setup.sh
colcon build --symlink-install --packages-up-to rclcpp \
    --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
