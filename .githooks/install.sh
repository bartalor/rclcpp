#!/usr/bin/env bash
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
git -C "$repo_root" config core.hooksPath .githooks
