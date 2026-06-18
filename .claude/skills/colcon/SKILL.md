---
name: colcon
description: Use when running colcon to build the ROS2 workspace — where to run it from and how to scope the build so it doesn't rebuild everything.
---

# Colcon

Run from `/opt/overlay_ws`, never the source tree (it dumps `log/` in CWD).

Default to a scoped build, not a full-workspace rebuild. After fetching a few upstream commits, `colcon build --packages-up-to <pkg>` (changed pkgs + dependents) or `--packages-select <pkg>` (just those pkgs) finishes in a fraction of the time. Bare `colcon build` rebuilds every package in the workspace — only do that when you actually want that.

## Commit before long builds

Commit code edits *before* kicking off a long colcon build or test run, not after. If the build fails or tests reveal a problem, amend the commit.

Why: the user's workflow is commit-first, amend-on-failure. While a multi-minute build runs, the user often reads the diff in the editor — an accidental keystroke can mutate the working tree silently. If the tree was already committed, the stray edit shows up as fresh dirty state and is obvious. If it wasn't, the stray edit silently merges into "pending changes" and ships in the next commit.

So: edits in place → commit → kick off build → amend if needed.
