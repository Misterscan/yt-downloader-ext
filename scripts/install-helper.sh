#!/bin/zsh
set -euo pipefail

# This script installs the launch agent for the YouTube download helper.
# Edit these variables for your own setup. The launch agent will run a script that checks for new downloads every minute.
LABEL="com.tonyk.ytdownload-helper"
WORKDIR="/Volumes/CrucialX9/download-yt"
PLIST_SRC="$WORKDIR/scripts/$LABEL.plist"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENT_DIR/$LABEL.plist"

mkdir -p "$LAUNCH_AGENT_DIR"

cp "$PLIST_SRC" "$PLIST_DEST"

# Unload first if it already exists.
launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started: $LABEL"
echo "Status: launchctl print gui/$(id -u)/$LABEL | head -n 20"
echo "Logs: tail -f /tmp/$LABEL.err.log"
