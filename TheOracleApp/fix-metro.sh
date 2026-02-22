#!/bin/bash

echo "🔧 Fixing Metro Bundler File Limits"

# Method 1: Set limits for current session
echo "Setting limits for current session..."
ulimit -n 65536
ulimit -u 2048

# Method 2: Create temporary watchman config
echo "Configuring watchman..."
watchman watch-del-all 2>/dev/null || echo "Watchman not installed (optional)"

# Method 3: Clear Metro cache
echo "Clearing Metro cache..."
rm -rf node_modules/.cache 2>/dev/null
rm -rf /tmp/metro-* 2>/dev/null

# Method 4: Start Metro with reduced watchers
echo "Starting Metro with optimized settings..."
export WATCHMAN_LOG_LEVEL=0
export CI=true
npx react-native start --reset-cache