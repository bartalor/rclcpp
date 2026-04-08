FROM ros:rolling

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gdb \
    clangd \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Rename the existing ubuntu user (UID 1000) to match the host user
ARG USERNAME=bar
RUN usermod -l $USERNAME -d /home/$USERNAME -m ubuntu \
    && groupmod -n $USERNAME ubuntu \
    && apt-get update && apt-get install -y sudo \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# Set up ROS 2 environment for the user
RUN echo "source /opt/ros/rolling/setup.bash" >> /home/$USERNAME/.bashrc

USER $USERNAME
WORKDIR /home/$USERNAME/ws
