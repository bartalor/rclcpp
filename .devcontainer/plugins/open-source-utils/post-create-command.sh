#!/bin/bash
set -eo pipefail

LINE='source ~/dotfiles/open-source-utils/activate.sh'
grep -qxF "$LINE" ~/.bashrc || echo "$LINE" >> ~/.bashrc
