#!/usr/bin/env bash
# Build and start IronPulse (MariaDB + GUI) with Docker, showing the window on this X11 display.
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

export APP_UID="$(id -u)" APP_GID="$(id -g)" DISPLAY="${DISPLAY:-:0}"
# Use the host's timezone for log timestamps
export TZ="${TZ:-$(timedatectl show -p Timezone --value 2>/dev/null || echo UTC)}"
mkdir -p exports

# Allow only your own user (the container runs with your UID) to use the X display.
if command -v xhost >/dev/null 2>&1; then
    xhost +SI:localuser:"$(id -un)" >/dev/null
fi

# If the active Docker context (e.g. Docker Desktop) isn't running, use the system daemon.
if ! docker info >/dev/null 2>&1; then
    export DOCKER_CONTEXT=default
fi

docker compose up --build "$@"
