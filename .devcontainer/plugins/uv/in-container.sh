#!/bin/bash
set -eo pipefail

LINE='export PATH="$HOME/.local/bin:$PATH"'
grep -qxF "$LINE" ~/.bashrc || echo "$LINE" >> ~/.bashrc
