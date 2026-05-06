ARG FROM_IMAGE=ros:rolling
ARG OVERLAY_WS=/opt/overlay_ws

FROM $FROM_IMAGE

ARG DEBIAN_FRONTEND=noninteractive
RUN echo '\
APT::Install-Recommends "0";\n\
APT::Install-Suggests "0";\n\
' > /etc/apt/apt.conf.d/01norecommend
ENV PYTHONUNBUFFERED=1

# install dev tools (deps come from rosdep at container start)
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && \
    apt-get upgrade -y --with-new-pkgs && \
    apt-get install -y \
      bash-completion \
      build-essential \
      cmake \
      gdb \
      gh \
      clangd \
      git \
      ccache \
      lld \
      python3-pip \
      python3-colcon-common-extensions \
      python3-rosdep \
    && pip3 install --break-system-packages \
      git+https://github.com/ruffsl/colcon-cache.git@a937541bfc496c7a267db7ee9d6cceca61e470ca \
    && rm -rf /var/lib/apt/lists/*

# keep apt lists for runtime rosdep install
RUN mv /etc/apt/apt.conf.d/docker-clean /etc/apt/

# allow ubuntu user passwordless sudo for lifecycle scripts
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu && \
    chmod 0440 /etc/sudoers.d/ubuntu

ARG OVERLAY_WS
ENV OVERLAY_WS=$OVERLAY_WS

# named volume mount inherits ownership from this dir on first creation
RUN mkdir -p $OVERLAY_WS && chown ubuntu:ubuntu $OVERLAY_WS
