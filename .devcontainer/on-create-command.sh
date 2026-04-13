#!/bin/bash
set -eo pipefail

git config --global --add safe.directory "*"

ROS2_REPOS_URL="https://raw.githubusercontent.com/ros2/ros2/rolling/ros2.repos"
WS="/home/ws"

# Ensure /home/ws exists and is owned by current user
sudo mkdir -p "$WS"
sudo chown "$(whoami)" "$WS"
mkdir -p "$WS/src/ros2"

# Symlink rclcpp source into workspace
ln -sfn "$HOME/src/ros2/rclcpp" "$WS/src/ros2/rclcpp"

cd "$WS"

# vcs import — re-run only when upstream ros2.repos changes
repos_file=$(mktemp)
trap 'rm -f "$repos_file"' EXIT
curl -fsSL "$ROS2_REPOS_URL" -o "$repos_file"
repos_hash=$(sha256sum "$repos_file" | cut -d' ' -f1)
if [ ! -f "$WS/.vcs-imported" ] || [ "$(cat "$WS/.vcs-imported")" != "$repos_hash" ]; then
    vcs import --input "$repos_file" --skip-existing src
    echo "$repos_hash" > "$WS/.vcs-imported"
fi

# rosdep install — apt packages live in the container, not the volume.
# Must run on every rebuild since container filesystem is ephemeral.
sudo apt-get update
rosdep update
rosdep install --from-paths src --ignore-src -y

# Run initial build via update-content-command
"$HOME/src/ros2/rclcpp/.devcontainer/update-content-command.sh"
