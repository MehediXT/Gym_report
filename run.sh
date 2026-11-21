#!/usr/bin/env bash
# Launcher script for IronPulse Fitness Management App

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Optional user-space Tk/Python libraries (only used if they exist)
LOCAL="$HOME/.local/usr"
[ -d "$LOCAL/lib" ] && export LD_LIBRARY_PATH="$LOCAL/lib:$LOCAL/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
[ -d "$LOCAL/share/tcltk/tk8.6" ] && export TK_LIBRARY="$LOCAL/share/tcltk/tk8.6"
[ -d "/usr/share/tcltk/tcl8.6" ] && export TCL_LIBRARY="/usr/share/tcltk/tcl8.6"

# Prefer the project virtual environment if it exists
PY="python3"
[ -x "$DIR/.venv/bin/python" ] && PY="$DIR/.venv/bin/python"

echo "Starting IronPulse Fitness Management System..."
exec "$PY" main.py "$@"
