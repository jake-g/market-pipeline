#!/bin/bash
set -e

echo "🧹 Cleaning up any locked Playwright or Chromium processes..."
pkill -f "Google Chrome for Testing" || true
pkill -f "Chromium" || true

LOCKFILE="$HOME/.notebooklm/browser_profile/SingletonLock"
if [ -f "$LOCKFILE" ]; then
    echo "🔓 Removing stale profile lock: $LOCKFILE"
    rm -f "$LOCKFILE"
fi

echo "✅ Environment unlocked."
echo "🔐 Spawning notebooklm login flow..."
notebooklm login
