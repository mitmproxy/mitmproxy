#!/bin/bash
# Local Release Testing Script
# Tests the release build locally before pushing to production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APP_NAME="Oximy"
BUNDLE_ID="com.oximy.mac"

echo "=== Oximy Local Release Test ==="
echo ""

# Parse arguments
CLEAN_PREFS=false
BUILD_CONFIG="release"
SKIP_BUILD=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --clean) CLEAN_PREFS=true ;;
        --debug) BUILD_CONFIG="debug" ;;
        --skip-build) SKIP_BUILD=true ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --clean       Clear app preferences (simulate fresh install)"
            echo "  --debug       Build in debug mode (faster, with symbols)"
            echo "  --skip-build  Skip building, just run existing build"
            echo "  --help        Show this help message"
            echo ""
            echo "Testing workflow:"
            echo "  1. $0 --clean          # Test fresh install experience"
            echo "  2. $0                   # Test normal launch (with persisted state)"
            echo "  3. $0 --debug --clean   # Quick debug build for fresh install"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Kill any running instance
echo "[1/5] Killing any running Oximy instance..."
pkill -x "Oximy" 2>/dev/null || true
sleep 1

# Clean preferences if requested
if [ "$CLEAN_PREFS" = true ]; then
    echo "[2/5] Clearing app preferences (simulating fresh install)..."
    defaults delete "$BUNDLE_ID" 2>/dev/null || true
    rm -rf "$HOME/.oximy" 2>/dev/null || true
    echo "    ✓ Preferences cleared"
else
    echo "[2/5] Keeping existing preferences"
fi

# Build the app
if [ "$SKIP_BUILD" = false ]; then
    echo "[3/5] Building in $BUILD_CONFIG mode..."
    BUILD_CONFIG="$BUILD_CONFIG" "$SCRIPT_DIR/build-release.sh"
else
    echo "[3/5] Skipping build (--skip-build specified)"
    if [ ! -d "$BUILD_DIR/$APP_NAME.app" ]; then
        echo "    ERROR: No existing build found at $BUILD_DIR/$APP_NAME.app"
        echo "    Run without --skip-build first"
        exit 1
    fi
fi

# Show current preferences state
echo ""
echo "[4/5] Current app state:"
echo "    UserDefaults:"
defaults read "$BUNDLE_ID" 2>/dev/null | head -20 || echo "    (none - fresh install)"
echo ""
echo "    ~/.oximy directory:"
ls -la "$HOME/.oximy" 2>/dev/null || echo "    (none - fresh install)"
echo ""

# Open the app
echo "[5/5] Opening $APP_NAME.app..."
echo ""
open "$BUILD_DIR/$APP_NAME.app"

echo ""
echo "=== Test Instructions ==="
echo ""
echo "1. VERIFY POPOVER: The app should show a popover automatically on fresh install"
echo "   - If phase is 'enrollment' or 'setup', popover should appear"
echo "   - Check Console.app for '[OximyApp]' logs to debug"
echo ""
echo "2. VERIFY ICON: Check the app icon in Finder/Launchpad"
echo "   - Should fill the entire icon area"
echo "   - No double-rounded corners or bleed"
echo "   - Path: $BUILD_DIR/$APP_NAME.app"
echo ""
echo "3. VIEW LOGS: Run this to see app logs in real-time:"
echo "   log stream --predicate 'process == \"Oximy\"' --level debug"
echo ""
echo "4. QUICK LOG CHECK: Run this to see recent logs:"
echo "   log show --predicate 'process == \"Oximy\"' --last 1m --style compact"
echo ""

# Wait for app to start and show some logs
echo "Waiting 3 seconds then showing recent logs..."
sleep 3
echo ""
echo "=== Recent App Logs ==="
log show --predicate 'process == "Oximy"' --last 10s --style compact 2>/dev/null | grep -v "^Timestamp" | tail -30 || echo "(no logs found)"
