#!/bin/bash
# Quick local notarization script
# Run after build-release.sh to test notarization

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"

# Find the DMG
DMG_PATH=$(ls -t "$BUILD_DIR"/*.dmg 2>/dev/null | head -1)

if [ -z "$DMG_PATH" ] || [ ! -f "$DMG_PATH" ]; then
    echo "ERROR: No DMG found in $BUILD_DIR"
    echo "Run build-release.sh first"
    exit 1
fi

echo "=== Local Notarization Test ==="
echo "DMG: $DMG_PATH"
echo ""

# Verify signature first
echo "[1/3] Verifying signature..."
APP_PATH="$BUILD_DIR/Oximy.app"
if [ -d "$APP_PATH" ]; then
    if codesign --verify --deep --strict --verbose=2 "$APP_PATH" 2>&1; then
        echo "✓ Signature valid"
    else
        echo "✗ Signature INVALID - cannot notarize"
        exit 1
    fi
fi

# Submit for notarization
echo ""
echo "[2/3] Submitting for notarization..."

# Check for keychain profile first
if xcrun notarytool history --keychain-profile "oximy-notarize" 2>/dev/null | head -1; then
    echo "Using keychain profile: oximy-notarize"
    xcrun notarytool submit "$DMG_PATH" \
        --keychain-profile "oximy-notarize" \
        --wait
    RESULT=$?
else
    # Need credentials
    if [ -z "$APPLE_ID" ]; then
        echo "No keychain profile found."
        echo ""
        echo "To set up keychain profile (recommended):"
        echo "  xcrun notarytool store-credentials 'oximy-notarize' \\"
        echo "    --apple-id 'your-apple-id@email.com' \\"
        echo "    --team-id 'K6H6LCASRA'"
        echo ""
        echo "Or provide credentials via environment variables:"
        echo "  APPLE_ID='...' APPLE_APP_PASSWORD='...' $0"
        exit 1
    fi

    echo "Using credentials from environment"
    xcrun notarytool submit "$DMG_PATH" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --team-id "K6H6LCASRA" \
        --wait
    RESULT=$?
fi

if [ $RESULT -ne 0 ]; then
    echo ""
    echo "✗ Notarization failed!"
    echo ""
    echo "To get the log, find the submission ID above and run:"
    echo "  xcrun notarytool log <submission-id> --keychain-profile oximy-notarize notarization-log.json"
    exit 1
fi

# Staple
echo ""
echo "[3/3] Stapling notarization ticket..."
xcrun stapler staple "$DMG_PATH"

echo ""
echo "=== Success! ==="
echo ""
echo "Notarized DMG: $DMG_PATH"
echo ""
echo "The DMG is ready for distribution."
