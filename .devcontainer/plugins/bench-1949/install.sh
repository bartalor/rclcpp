#!/usr/bin/env bash
# Image-build steps for bench-rclcpp-1949: ClangBuildAnalyzer (-ftime-trace
# aggregator) and the Python deps run.py / aggregate.py / plot.py need.
set -euo pipefail

git clone --depth 1 --branch v1.5.0 \
    https://github.com/aras-p/ClangBuildAnalyzer.git /tmp/cba
cmake -S /tmp/cba -B /tmp/cba/build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/cba/build --parallel
install -m 0755 /tmp/cba/build/ClangBuildAnalyzer /usr/local/bin/
rm -rf /tmp/cba

pip3 install --break-system-packages \
    matplotlib \
    numpy
