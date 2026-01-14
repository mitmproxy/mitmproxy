#!/bin/bash
# Local Notarization Test Script
# Tests the build, signing, and notarization process locally before using GitHub Actions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APP_NAME="Oximy"
VERSION="${VERSION:-0.0.1-local-test}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Local Notarization Test ==="
echo "Version: $VERSION"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check for Developer ID
DEVELOPER_ID="Developer ID Application: Oximy, Inc. (K6H6LCASRA)"
if ! security find-identity -v -p codesigning | grep -q "$DEVELOPER_ID"; then
    echo -e "${RED}ERROR: Developer ID certificate not found${NC}"
    echo "Expected: $DEVELOPER_ID"
    echo "Available identities:"
    security find-identity -v -p codesigning
    exit 1
fi
echo -e "${GREEN}✓ Developer ID certificate found${NC}"

# Check for notarytool credentials
if [ -z "$APPLE_ID" ] || [ -z "$APPLE_APP_PASSWORD" ]; then
    echo -e "${YELLOW}NOTE: APPLE_ID and APPLE_APP_PASSWORD not set${NC}"
    echo "You can set them or store in keychain:"
    echo "  xcrun notarytool store-credentials 'oximy-notarize' --apple-id YOUR_APPLE_ID --team-id K6H6LCASRA --password YOUR_APP_PASSWORD"
    echo ""
    echo "Then this script will use the keychain profile."
    USE_KEYCHAIN_PROFILE=true
else
    USE_KEYCHAIN_PROFILE=false
    echo -e "${GREEN}✓ Apple credentials found in environment${NC}"
fi

# Step 1: Build
echo ""
echo "[1/6] Building app..."
cd "$PROJECT_DIR"
export DEVELOPER_ID
"$SCRIPT_DIR/build-release.sh"

APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
DMG_PATH="$BUILD_DIR/$APP_NAME-$VERSION.dmg"

# Step 2: Verify code signature before notarization
echo ""
echo "[2/6] Verifying code signature..."

echo "  Checking main binary..."
codesign -dvvv "$APP_BUNDLE/Contents/MacOS/Oximy" 2>&1 | head -20

echo ""
echo "  Deep verification of app bundle..."
if codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE" 2>&1; then
    echo -e "${GREEN}✓ App bundle signature is valid${NC}"
else
    echo -e "${RED}✗ App bundle signature verification failed${NC}"
    echo ""
    echo "Checking individual components..."

    # Check main binary
    echo "  Main binary:"
    codesign -vvv "$APP_BUNDLE/Contents/MacOS/Oximy" 2>&1 || true

    # Check frameworks
    if [ -d "$APP_BUNDLE/Contents/Frameworks" ]; then
        echo ""
        echo "  Frameworks:"
        find "$APP_BUNDLE/Contents/Frameworks" -name "*.framework" -o -name "*.dylib" | while read f; do
            echo "    $(basename "$f"):"
            codesign -vvv "$f" 2>&1 | head -3 || true
        done
    fi

    exit 1
fi

# Step 3: Check for hardened runtime
echo ""
echo "[3/6] Checking hardened runtime flags..."
ENTITLEMENTS=$(codesign -d --entitlements :- "$APP_BUNDLE" 2>/dev/null || echo "")
FLAGS=$(codesign -dvv "$APP_BUNDLE" 2>&1 | grep "flags=" || echo "flags=none")
echo "  Flags: $FLAGS"

if echo "$FLAGS" | grep -q "runtime"; then
    echo -e "${GREEN}✓ Hardened runtime enabled${NC}"
else
    echo -e "${RED}✗ Hardened runtime NOT enabled${NC}"
    echo "  The build script should use --options runtime flag"
    exit 1
fi

# Step 4: Create DMG
echo ""
echo "[4/6] Creating DMG..."
if [ -f "$DMG_PATH" ]; then
    rm -f "$DMG_PATH"
fi
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$APP_BUNDLE" \
    -ov -format UDZO \
    "$DMG_PATH"
if [ ! -f "$DMG_PATH" ]; then
    echo -e "${RED}ERROR: Failed to create DMG at $DMG_PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✓ DMG created: $DMG_PATH${NC}"
echo "  Size: $(du -h "$DMG_PATH" | cut -f1)"

# Step 5: Submit for notarization
echo ""
echo "[5/6] Submitting for notarization..."

if [ "$USE_KEYCHAIN_PROFILE" = true ]; then
    # Check if keychain profile exists
    if xcrun notarytool history --keychain-profile "oximy-notarize" --limit 1 &>/dev/null; then
        echo "  Using keychain profile: oximy-notarize"
        NOTARIZE_CMD="xcrun notarytool submit '$DMG_PATH' --keychain-profile 'oximy-notarize' --wait"
    else
        echo -e "${YELLOW}Keychain profile 'oximy-notarize' not found.${NC}"
        echo ""
        echo "To create it, run:"
        echo "  xcrun notarytool store-credentials 'oximy-notarize' --apple-id YOUR_APPLE_ID --team-id K6H6LCASRA"
        echo ""
        echo "Or set environment variables:"
        echo "  export APPLE_ID='your-apple-id@email.com'"
        echo "  export APPLE_APP_PASSWORD='xxxx-xxxx-xxxx-xxxx'"
        echo ""
        read -p "Enter your Apple ID (or press Enter to skip notarization): " APPLE_ID
        if [ -z "$APPLE_ID" ]; then
            echo "Skipping notarization."
            echo ""
            echo "=== Build Complete (Not Notarized) ==="
            echo "App: $APP_BUNDLE"
            echo "DMG: $DMG_PATH"
            exit 0
        fi
        read -s -p "Enter App-Specific Password: " APPLE_APP_PASSWORD
        echo ""
        USE_KEYCHAIN_PROFILE=false
    fi
fi

if [ "$USE_KEYCHAIN_PROFILE" = false ]; then
    NOTARIZE_CMD="xcrun notarytool submit '$DMG_PATH' --apple-id '$APPLE_ID' --password '$APPLE_APP_PASSWORD' --team-id 'K6H6LCASRA' --wait"
fi

echo "  Submitting..."
echo "  (This may take 5-15 minutes)"

# Create a temp file for output
NOTARIZE_OUTPUT=$(mktemp)

# Run notarization and capture output
set +e
eval $NOTARIZE_CMD 2>&1 | tee "$NOTARIZE_OUTPUT"
NOTARIZE_EXIT=$?
set -e

# Extract submission ID
SUBMISSION_ID=$(grep -o 'id: [a-f0-9-]*' "$NOTARIZE_OUTPUT" | head -1 | cut -d' ' -f2)

if [ $NOTARIZE_EXIT -ne 0 ] || grep -q "Invalid" "$NOTARIZE_OUTPUT"; then
    echo ""
    echo -e "${RED}✗ Notarization failed${NC}"

    # Fetch detailed log
    if [ -n "$SUBMISSION_ID" ]; then
        echo ""
        echo "Fetching detailed log for submission: $SUBMISSION_ID"
        LOG_PATH="$BUILD_DIR/notarization-log.json"

        if [ "$USE_KEYCHAIN_PROFILE" = true ]; then
            xcrun notarytool log "$SUBMISSION_ID" --keychain-profile "oximy-notarize" "$LOG_PATH" 2>/dev/null || true
        else
            xcrun notarytool log "$SUBMISSION_ID" --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" --team-id "K6H6LCASRA" "$LOG_PATH" 2>/dev/null || true
        fi

        if [ -f "$LOG_PATH" ]; then
            echo ""
            echo "=== Notarization Log ==="
            cat "$LOG_PATH"
            echo ""

            # Parse issues
            echo "=== Issues Summary ==="
            python3 -c "
import json
with open('$LOG_PATH') as f:
    log = json.load(f)
    issues = log.get('issues', [])
    if issues:
        for issue in issues:
            print(f\"  {issue.get('severity', 'unknown').upper()}: {issue.get('path', 'unknown')}\")
            print(f\"    {issue.get('message', 'No message')}\")
            if issue.get('docUrl'):
                print(f\"    Doc: {issue.get('docUrl')}\")
            print()
    else:
        print('  No issues found in log')
" 2>/dev/null || cat "$LOG_PATH"
        fi
    fi

    rm -f "$NOTARIZE_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓ Notarization successful${NC}"

# Step 6: Staple the notarization ticket
echo ""
echo "[6/6] Stapling notarization ticket..."
xcrun stapler staple "$DMG_PATH"
echo -e "${GREEN}✓ Stapled successfully${NC}"

# Final verification
echo ""
echo "=== Final Verification ==="
spctl -a -t open --context context:primary-signature -v "$DMG_PATH" 2>&1 || true

rm -f "$NOTARIZE_OUTPUT"

echo ""
echo -e "${GREEN}=== Success! ===${NC}"
echo ""
echo "Notarized DMG: $DMG_PATH"
echo ""
echo "You can now upload this to GitHub Releases or distribute it."
