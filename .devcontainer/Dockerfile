ARG FROM_IMAGE=ros:rolling
ARG UNDERLAY_WS=/opt/underlay_ws
ARG OVERLAY_WS=/opt/overlay_ws

# multi-stage for caching
FROM $FROM_IMAGE AS cacher

# clone underlay source
ARG UNDERLAY_WS
WORKDIR $UNDERLAY_WS/src
RUN curl -fsSL https://raw.githubusercontent.com/ros2/ros2/rolling/ros2.repos -o ../ros2.repos \
    && vcs import ./ < ../ros2.repos

# copy manifests for caching
WORKDIR /opt
RUN find . -name "src" -type d \
      -mindepth 1 -maxdepth 2 -printf '%P\n' \
      | xargs -I % mkdir -p /tmp/opt/% && \
    find . -name "package.xml" \
      | xargs cp --parents -t /tmp/opt && \
    find . -name "COLCON_IGNORE" \
      | xargs cp --parents -t /tmp/opt || true

# multi-stage for building
FROM $FROM_IMAGE AS builder

# config dependencies install
ARG DEBIAN_FRONTEND=noninteractive
RUN echo '\
APT::Install-Recommends "0";\n\
APT::Install-Suggests "0";\n\
' > /etc/apt/apt.conf.d/01norecommend
ENV PYTHONUNBUFFERED 1

# install CI dependencies
RUN apt-get update && \
    apt-get upgrade -y --with-new-pkgs && \
    apt-get install -y \
      sudo \
      build-essential \
      cmake \
      gdb \
      clangd \
      git \
      ccache \
      lld \
      python3-pip \
      python3-colcon-common-extensions \
      python3-rosdep \
      python3-vcstool \
    && pip3 install --break-system-packages \
      git+https://github.com/ruffsl/colcon-cache.git@a937541bfc496c7a267db7ee9d6cceca61e470ca \
    && rosdep update \
    && colcon mixin update \
    && colcon metadata update \
    && rm -rf /var/lib/apt/lists/*

# install underlay dependencies
ARG UNDERLAY_WS
ENV UNDERLAY_WS $UNDERLAY_WS
WORKDIR $UNDERLAY_WS
COPY --from=cacher /tmp/$UNDERLAY_WS ./
RUN . /opt/ros/$ROS_DISTRO/setup.sh && \
    apt-get update && rosdep install -q -y \
      --from-paths src \
      --ignore-src \
    && rm -rf /var/lib/apt/lists/*

# build underlay source
COPY --from=cacher $UNDERLAY_WS ./
ARG UNDERLAY_MIXINS="release ccache lld"
ARG CCACHE_DIR="$UNDERLAY_WS/.ccache"
ENV MAKEFLAGS="-j2"
RUN . /opt/ros/$ROS_DISTRO/setup.sh && \
    colcon cache lock && \
    colcon build \
      --symlink-install \
      --mixin $UNDERLAY_MIXINS \
      --parallel-workers 4 \
      --packages-up-to rclcpp \
      --event-handlers console_direct+

# multi-stage for developing
FROM builder AS dever

ARG USERNAME=bar
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# create dev user
RUN if id -u $USER_UID 2>/dev/null; then userdel "$(id -un $USER_UID)"; fi \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# edit apt for caching
RUN mv /etc/apt/apt.conf.d/docker-clean /etc/apt/

ENV SHELL=/bin/bash

# source underlay for shell
ARG OVERLAY_WS
ENV OVERLAY_WS $OVERLAY_WS
RUN echo "source \"$UNDERLAY_WS/install/setup.bash\"" >> /etc/bash.bashrc

USER $USERNAME
CMD ["/bin/bash"]
