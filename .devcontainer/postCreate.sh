#!/bin/bash
set -e

# Ensure /home/ws ownership (volume may already have data)
sudo mkdir -p /home/ws/src/ros2
sudo chown -R "$(whoami)" /home/ws

# Symlink rclcpp source into workspace
ln -sfn "$HOME/src/ros2/rclcpp" /home/ws/src/ros2/rclcpp

cd /home/ws

# Only run expensive vcs import if not already done
if [ ! -f /home/ws/.vcs-imported ]; then
    vcs import --input https://raw.githubusercontent.com/ros2/ros2/rolling/ros2.repos --skip-existing src
    touch /home/ws/.vcs-imported
fi

# rosdep install — apt packages live in the container, not the volume.
# Must run on every rebuild, but it's fast when packages are already installed.
sudo apt-get update
rosdep update
rosdep install --from-paths src --ignore-src -y

# Only run colcon build if not already done
. /opt/ros/rolling/setup.sh
if [ ! -f /home/ws/.colcon-built ]; then
    colcon build --symlink-install --packages-up-to rclcpp \
        --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    touch /home/ws/.colcon-built
fi
