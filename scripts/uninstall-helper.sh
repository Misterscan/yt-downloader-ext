#!/bin/zsh
set -euo pipefail

# This script uninstalls the launch agent for the YouTube download helper.
# Edit this variable for your own setup.
LABEL="com.tonyk.ytdownload-helper"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true
launchctl disable "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST_DEST"

echo "Uninstalled: $LABEL"
