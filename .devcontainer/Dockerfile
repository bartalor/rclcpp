FROM ros:rolling
ARG USERNAME=bar
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Delete conflicting user, create dev user, and install all apt packages
RUN if id -u $USER_UID ; then userdel "$(id -un $USER_UID)" ; fi \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        sudo \
        python3-pip \
        build-essential \
        cmake \
        gdb \
        clangd \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-vcstool \
        git \
        ccache \
        lld \
    && pip3 install --break-system-packages \
        git+https://github.com/ruffsl/colcon-cache.git@a937541bfc496c7a267db7ee9d6cceca61e470ca \
    && colcon mixin update default \
    && colcon metadata update \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

ENV SHELL=/bin/bash

# Set up ROS 2 environment for the user
RUN echo "source /opt/ros/rolling/setup.bash" >> /home/$USERNAME/.bashrc

USER $USERNAME
CMD ["/bin/bash"]
