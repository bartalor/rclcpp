---
name: colcon
description: Use when running colcon to build the ROS2 workspace — where to run it from and how to scope the build so it doesn't rebuild everything.
---

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.
