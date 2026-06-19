ARG FROM_IMAGE=ros:rolling-ros-base-noble@sha256:723ba4fdcc232b43d7ee1effbee2414b3990321c22d3c9dfd8592ff17b2cd45a
ARG OVERLAY_WS=/opt/overlay_ws

FROM $FROM_IMAGE

ARG DEBIAN_FRONTEND=noninteractive
RUN echo '\
APT::Install-Recommends "0";\n\
APT::Install-Suggests "0";\n\
' > /etc/apt/apt.conf.d/01norecommend
ENV PYTHONUNBUFFERED=1

# add github cli apt repo
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list

# install dev tools (deps come from rosdep at container start)
RUN apt-get update && \
    apt-get upgrade -y --with-new-pkgs && \
    apt-get install -y \
      bash-completion \
      build-essential \
      cmake \
      gdb \
      gh \
      clang \
      clangd \
      git \
      openssh-client \
      ccache \
      lld \
      linux-tools-generic \
      lsof \
      heaptrack \
      valgrind \
      libc6-dbg \
      python3-pip \
      python3-colcon-common-extensions \
      python3-colcon-mixin \
      python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# uv (static binary, no host deps)
RUN curl -LsSf https://astral.sh/uv/install.sh | \
    UV_INSTALL_DIR=/usr/local/bin sh

# share the colcon mixin index (release, ccache, compile-commands, lld, ...)
# system-wide via COLCON_HOME so root and ubuntu read the same config.
ENV COLCON_HOME=/etc/colcon
RUN colcon mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml && \
    colcon mixin update default && \
    chmod -R a+rX /etc/colcon

# colcon-cache (third-party plugin, pinned to a known-good revision)
RUN pip3 install --break-system-packages \
    git+https://github.com/ruffsl/colcon-cache.git@a937541bfc496c7a267db7ee9d6cceca61e470ca

# keep apt lists for runtime rosdep install
RUN mv /etc/apt/apt.conf.d/docker-clean /etc/apt/

# allow ubuntu user passwordless sudo for lifecycle scripts
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu && \
    chmod 0440 /etc/sudoers.d/ubuntu

ARG OVERLAY_WS
ENV OVERLAY_WS=$OVERLAY_WS

# named volume mounts inherit ownership from these dirs on first creation
RUN mkdir -p $OVERLAY_WS /tmp/.ccache && \
    chown ubuntu:ubuntu $OVERLAY_WS /tmp/.ccache

# pre-create user dirs so docker auto-created bind-mount parents don't end up root-owned
RUN mkdir -p /home/ubuntu/.config/git /home/ubuntu/.claude && \
    chown -R ubuntu:ubuntu /home/ubuntu/.config /home/ubuntu/.claude
