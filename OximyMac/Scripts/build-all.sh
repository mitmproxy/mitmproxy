#!/bin/bash

# Build script for Oximy Mac App
# Builds, signs, and packages the app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APP_NAME="Oximy"

# Signing identities
APP_SIGNING_IDENTITY="Developer ID Application: Oximy, Inc. (K6H6LCASRA)"
TEAM_ID="K6H6LCASRA"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Oximy Mac Build Script                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Clean build directory
echo -e "${YELLOW}Cleaning build directory...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Step 1: Build the main app with SPM
echo -e "\n${GREEN}Step 1: Building main app with Swift Package Manager...${NC}"
cd "$PROJECT_DIR"
swift build -c release

# Create app bundle
echo -e "\n${YELLOW}Creating app bundle...${NC}"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS/MacOS"
RESOURCES_DIR="$CONTENTS/Resources"

mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy main executable
cp "$PROJECT_DIR/.build/release/OximyMac" "$MACOS_DIR/$APP_NAME"

# Copy Info.plist (with variables replaced)
sed -e 's/$(EXECUTABLE_NAME)/Oximy/g' \
    -e 's/$(PRODUCT_BUNDLE_IDENTIFIER)/com.oximy.mac/g' \
    -e 's/$(PRODUCT_NAME)/Oximy/g' \
    -e 's/$(DEVELOPMENT_LANGUAGE)/en/g' \
    "$PROJECT_DIR/Info.plist" > "$CONTENTS/Info.plist"

# Copy resources
if [ -d "$PROJECT_DIR/Resources" ]; then
    cp -R "$PROJECT_DIR/Resources/"* "$RESOURCES_DIR/" 2>/dev/null || true
fi

# Step 2: Sign the main app
echo -e "\n${GREEN}Step 2: Signing main app...${NC}"
if security find-identity -v -p codesigning | grep -q "$APP_SIGNING_IDENTITY"; then
    # Create entitlements
    cat > "$BUILD_DIR/app.entitlements" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.app-sandbox</key>
    <false/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
EOF

    codesign \
        --force \
        --sign "$APP_SIGNING_IDENTITY" \
        --entitlements "$BUILD_DIR/app.entitlements" \
        --options runtime \
        --timestamp \
        --deep \
        "$APP_BUNDLE"
    echo -e "${GREEN}App signed successfully${NC}"
else
    echo -e "${YELLOW}Signing identity not found, using ad-hoc signing for development${NC}"
    codesign --force --sign - --deep "$APP_BUNDLE"
fi

# Step 3: Verify signature
echo -e "\n${GREEN}Step 3: Verifying signature...${NC}"
echo "App signature:"
codesign -dv "$APP_BUNDLE" 2>&1 | head -5

# Print summary
echo -e "\n${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Build Complete                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "App bundle: $APP_BUNDLE"
echo ""
echo "To test:"
echo "  open $APP_BUNDLE"
echo ""
echo "To notarize for distribution:"
echo "  xcrun notarytool submit $APP_BUNDLE --keychain-profile 'AC_PASSWORD' --wait"
