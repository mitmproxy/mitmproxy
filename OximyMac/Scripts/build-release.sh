#!/bin/bash
# Oximy Release Build Script
# Creates a distributable .dmg installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APP_NAME="Oximy"
VERSION="${VERSION:-1.0.0}"

echo "=== Oximy Release Build ==="
echo "Version: $VERSION"
echo "Project: $PROJECT_DIR"
echo ""

# Clean previous build
echo "[1/6] Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build in release mode
echo "[2/6] Building in release mode..."
cd "$PROJECT_DIR"
swift build -c release

# Create app bundle structure
echo "[3/6] Creating app bundle..."
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy binary
cp ".build/release/OximyMac" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.oximy.mac</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 Oximy. All rights reserved.</string>
</dict>
</plist>
EOF

# Copy resources
echo "[4/6] Copying resources..."
if [ -d "$PROJECT_DIR/Resources" ]; then
    cp -R "$PROJECT_DIR/Resources/"* "$APP_BUNDLE/Contents/Resources/" 2>/dev/null || true
fi

# Copy logos
for logo in Oximy.png frame.png; do
    if [ -f "$PROJECT_DIR/Resources/$logo" ]; then
        cp "$PROJECT_DIR/Resources/$logo" "$APP_BUNDLE/Contents/Resources/"
    fi
done

# Copy bundled Python if exists
if [ -d "$PROJECT_DIR/Resources/python-embed" ]; then
    echo "    Copying bundled Python (~110MB)..."
    cp -R "$PROJECT_DIR/Resources/python-embed" "$APP_BUNDLE/Contents/Resources/"
fi

# Copy addon from mitmproxy source (single source of truth)
ADDON_SRC="$PROJECT_DIR/../mitmproxy/addons/oximy"
if [ -d "$ADDON_SRC" ]; then
    cp -R "$ADDON_SRC" "$APP_BUNDLE/Contents/Resources/oximy-addon"
    echo "    Copied addon from: $ADDON_SRC"
else
    echo "ERROR: Addon not found at $ADDON_SRC"
    exit 1
fi

# Code signing (stub - requires Developer ID)
echo "[5/6] Code signing..."
if [ -n "$DEVELOPER_ID" ]; then
    echo "    Signing with: $DEVELOPER_ID"
    codesign --deep --force --options runtime \
        --sign "$DEVELOPER_ID" \
        "$APP_BUNDLE"
else
    echo "    STUB: Skipping code signing (no DEVELOPER_ID set)"
    echo "    To sign, run: DEVELOPER_ID='Developer ID Application: Your Name' $0"
fi

# Create app icon from Oximy-rounded.png (with proper macOS rounded corners)
echo "[6/7] Creating app icon..."
ICON_SOURCE="$PROJECT_DIR/Resources/Oximy-rounded.png"
# Fall back to original if rounded version doesn't exist
if [ ! -f "$ICON_SOURCE" ]; then
    ICON_SOURCE="$PROJECT_DIR/Resources/Oximy.png"
fi
if [ -f "$ICON_SOURCE" ]; then
    ICONSET_DIR="$BUILD_DIR/AppIcon.iconset"
    mkdir -p "$ICONSET_DIR"

    # Generate icon sizes
    sips -z 16 16     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" 2>/dev/null
    sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" 2>/dev/null
    sips -z 32 32     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" 2>/dev/null
    sips -z 64 64     "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" 2>/dev/null
    sips -z 128 128   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" 2>/dev/null
    sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" 2>/dev/null
    sips -z 256 256   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" 2>/dev/null
    sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" 2>/dev/null
    sips -z 512 512   "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" 2>/dev/null
    sips -z 1024 1024 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512@2x.png" 2>/dev/null

    # Convert to icns
    iconutil -c icns "$ICONSET_DIR" -o "$APP_BUNDLE/Contents/Resources/AppIcon.icns" 2>/dev/null || true
    rm -rf "$ICONSET_DIR"
    echo "    Created AppIcon.icns from Oximy.png"
else
    echo "    WARNING: Oximy.png not found, skipping icon generation"
fi

# Create DMG using create-dmg (https://github.com/sindresorhus/create-dmg)
echo "[7/7] Creating DMG with create-dmg..."
DMG_NAME="$APP_NAME-$VERSION.dmg"
DMG_PATH="$BUILD_DIR/$DMG_NAME"

# Source nvm to get access to npm-installed create-dmg
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Check if create-dmg is available
if command -v create-dmg &> /dev/null; then
    cd "$BUILD_DIR"
    # Remove existing DMG if present
    rm -f "$DMG_PATH" 2>/dev/null || true
    rm -f "$APP_NAME $VERSION.dmg" 2>/dev/null || true

    # create-dmg automatically handles Applications symlink and styling
    create-dmg "$APP_BUNDLE" "$BUILD_DIR" --overwrite 2>&1 || true

    # create-dmg names files as "AppName VERSION.dmg", rename to our format
    if [ -f "$BUILD_DIR/$APP_NAME $VERSION.dmg" ]; then
        mv "$BUILD_DIR/$APP_NAME $VERSION.dmg" "$DMG_PATH"
    fi
else
    echo "    WARNING: create-dmg not found, falling back to basic DMG creation"
    # Fallback: simple DMG without styling
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$APP_BUNDLE" \
        -ov -format UDZO \
        "$DMG_PATH"
fi

echo ""
echo "=== Build Complete ==="
echo ""
echo "App Bundle: $APP_BUNDLE"
echo "DMG:        $DMG_PATH"
echo ""

if [ -z "$DEVELOPER_ID" ]; then
    echo "NOTE: App is unsigned. For distribution:"
    echo "  1. Set DEVELOPER_ID environment variable"
    echo "  2. Run this script again"
    echo "  3. Notarize with: xcrun notarytool submit $DMG_PATH"
fi

echo ""
echo "To test locally:"
echo "  open $APP_BUNDLE"
echo ""
