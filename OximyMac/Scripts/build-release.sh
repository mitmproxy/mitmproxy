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

# Copy addon
if [ -d "$PROJECT_DIR/Resources/oximy-addon" ]; then
    cp -R "$PROJECT_DIR/Resources/oximy-addon" "$APP_BUNDLE/Contents/Resources/"
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

# Create app icon from Oximy.png
echo "[6/7] Creating app icon..."
ICON_SOURCE="$PROJECT_DIR/Resources/Oximy.png"
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

# Create styled DMG
echo "[7/7] Creating styled DMG..."
DMG_NAME="$APP_NAME-$VERSION.dmg"
DMG_PATH="$BUILD_DIR/$DMG_NAME"
DMG_TEMP="$BUILD_DIR/dmg_temp.dmg"

# Create temporary directory for DMG contents
TEMP_DMG_DIR=$(mktemp -d)
DMG_CONTENTS="$TEMP_DMG_DIR/$APP_NAME"
mkdir -p "$DMG_CONTENTS"
mkdir -p "$DMG_CONTENTS/.background"

# Copy app
cp -R "$APP_BUNDLE" "$DMG_CONTENTS/"

# Create Applications symlink
ln -s /Applications "$DMG_CONTENTS/Applications"

# Create background image (simple orange gradient with arrow)
BACKGROUND="$DMG_CONTENTS/.background/background.png"
if [ -f "$PROJECT_DIR/Installer/DMG/background.png" ]; then
    cp "$PROJECT_DIR/Installer/DMG/background.png" "$BACKGROUND"
else
    # Generate a simple background using sips
    # Create base image from Oximy.png colors
    echo "    Generating DMG background..."

    # Use Python to create a simple background (fallback)
    python3 << 'PYEOF' || true
import subprocess
import os

width, height = 540, 380
bg_path = os.environ.get('BACKGROUND', '/tmp/dmg_bg.png')

# Create SVG
svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2d1f0f;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1a1209;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
  <path d="M 220 190 Q 270 190 270 190 L 270 170 L 320 200 L 270 230 L 270 210 Q 220 210 220 210 Z"
        fill="#ff6b35" opacity="0.9"/>
  <text x="270" y="300" text-anchor="middle" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, Helvetica" font-size="13" opacity="0.8">
    Drag Oximy to Applications
  </text>
</svg>'''

svg_path = '/tmp/dmg_bg.svg'
with open(svg_path, 'w') as f:
    f.write(svg)

# Try to convert SVG to PNG
try:
    # Use qlmanage (built-in macOS)
    subprocess.run(['qlmanage', '-t', '-s', str(width), '-o', '/tmp', svg_path],
                   capture_output=True)
    if os.path.exists(f'{svg_path}.png'):
        os.rename(f'{svg_path}.png', bg_path)
        print(f'Created background: {bg_path}')
except Exception as e:
    print(f'Could not create background: {e}')
PYEOF

    export BACKGROUND="$BACKGROUND"
    if [ -f "/tmp/dmg_bg.png" ]; then
        mv "/tmp/dmg_bg.png" "$BACKGROUND"
    fi
fi

# Create read-write DMG first
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_CONTENTS" \
    -ov -format UDRW \
    "$DMG_TEMP"

# Mount it
MOUNT_DIR=$(hdiutil attach -readwrite -noverify "$DMG_TEMP" | grep "/Volumes/$APP_NAME" | awk '{print $3}')

if [ -n "$MOUNT_DIR" ]; then
    echo "    Styling DMG window..."

    # Apply Finder view settings using AppleScript
    osascript << EOF
    tell application "Finder"
        tell disk "$APP_NAME"
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set bounds of container window to {400, 200, 940, 580}
            set viewOptions to the icon view options of container window
            set arrangement of viewOptions to not arranged
            set icon size of viewOptions to 100

            -- Set background if exists
            if exists file ".background:background.png" then
                set background picture of viewOptions to file ".background:background.png"
            end if

            -- Position icons
            set position of item "$APP_NAME.app" of container window to {130, 180}
            set position of item "Applications" of container window to {410, 180}

            close
            open
            update without registering applications
            delay 1
            close
        end tell
    end tell
EOF

    # Unmount
    hdiutil detach "$MOUNT_DIR" -quiet
fi

# Convert to compressed read-only DMG
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_PATH"
rm -f "$DMG_TEMP"

# Cleanup
rm -rf "$TEMP_DMG_DIR"

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
