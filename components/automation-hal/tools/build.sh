#!/bin/sh
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=${1:-"$project/build"}
cmake -S "$project" -B "$build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build "$build" --parallel "${AHAL_BUILD_JOBS:-2}"
(cd "$build" && cpack)
