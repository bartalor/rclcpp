---
name: upstream-pr
description: Use when preparing a pull request to upstream ros2/rclcpp. Points to where the PR conventions live, how we draft PRs locally, and the rule of matching style by reading recent commits.
---

# Preparing an upstream PR for ros2/rclcpp

## Where to find the conventions

- `/home/bar/src/ros2/rclcpp/CONTRIBUTING.md` — licensing and the DCO sign-off requirement (every commit needs `Signed-off-by:`).
- The `ros2/rclcpp` repo on GitHub — PR template (auto-applied), recent merged PRs for everything else.

## Drafting the PR locally

We write the PR description in a file inside this repo (e.g. `PR_DESCRIPTION.md`). It must **not** appear in the upstream PR diff — keep it on `bar/devcontainer` or otherwise off the feature branch you're pushing.

## Match style by reading recent commits

Before finalizing, look at recent merged commits in the area you're touching. Match their commit-message length, comment density, and test layout. Not too terse, not too verbose — mirror what's already there.
