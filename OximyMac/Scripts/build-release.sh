#!/bin/bash
# Oximy Release Build Script
# Creates a distributable .dmg installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APP_NAME="Oximy"
VERSION="${VERSION:-1.0.0}"
BUILD_CONFIG="${BUILD_CONFIG:-release}"  # Can be 'release' or 'debug'

# Architecture info (ARM64 native, Intel via Rosetta 2)
ARCH=$(uname -m)

echo "=== Oximy Build ==="
echo "Version: $VERSION"
echo "Configuration: $BUILD_CONFIG"
echo "Architecture: $ARCH (Intel Macs use Rosetta 2)"
echo "Project: $PROJECT_DIR"
echo ""

# Clean previous build
echo "[1/7] Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build
echo "[2/7] Building in $BUILD_CONFIG mode..."
cd "$PROJECT_DIR"
swift build -c "$BUILD_CONFIG"

# Create app bundle structure
echo "[3/7] Creating app bundle..."
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy binary
cp ".build/$BUILD_CONFIG/OximyMac" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

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
    <key>SUFeedURL</key>
    <string>https://github.com/OximyHQ/mitmproxy/releases/latest/download/appcast.xml</string>
    <key>SUPublicEDKey</key>
    <string>${SPARKLE_PUBLIC_KEY:-3oJZV2w0DvQ80LCetz3lgL+DwfsFFYfqxsFHPlj0KQE=}</string>
    <key>SUEnableAutomaticChecks</key>
    <true/>
    <key>SUAllowsAutomaticUpdates</key>
    <true/>
    <key>SUScheduledCheckInterval</key>
    <integer>86400</integer>
</dict>
</plist>
EOF

# Copy frameworks (Sparkle, Sentry)
echo "[4/7] Copying frameworks..."
mkdir -p "$APP_BUNDLE/Contents/Frameworks"

# Copy Sparkle.framework - check build output first, then artifacts
SPARKLE_FRAMEWORK="$PROJECT_DIR/.build/$BUILD_CONFIG/Sparkle.framework"
if [ ! -d "$SPARKLE_FRAMEWORK" ]; then
    # Fallback to xcframework artifacts
    SPARKLE_FRAMEWORK="$PROJECT_DIR/.build/artifacts/sparkle/Sparkle/Sparkle.xcframework/macos-arm64_x86_64/Sparkle.framework"
fi
if [ -d "$SPARKLE_FRAMEWORK" ]; then
    echo "    Copying Sparkle.framework from $SPARKLE_FRAMEWORK..."
    cp -R "$SPARKLE_FRAMEWORK" "$APP_BUNDLE/Contents/Frameworks/"
else
    echo "    ERROR: Sparkle.framework not found"
    echo "    Run 'swift build -c $BUILD_CONFIG' first to fetch Sparkle package"
    exit 1
fi

# Copy Sentry.framework - check build output first, then artifacts
SENTRY_FRAMEWORK="$PROJECT_DIR/.build/$BUILD_CONFIG/Sentry.framework"
if [ ! -d "$SENTRY_FRAMEWORK" ]; then
    # Fallback to xcframework artifacts (dynamic version for macOS)
    SENTRY_FRAMEWORK="$PROJECT_DIR/.build/artifacts/sentry-cocoa/Sentry-Dynamic/Sentry-Dynamic.xcframework/macos-arm64_x86_64/Sentry.framework"
fi
if [ -d "$SENTRY_FRAMEWORK" ]; then
    echo "    Copying Sentry.framework from $SENTRY_FRAMEWORK..."
    cp -R "$SENTRY_FRAMEWORK" "$APP_BUNDLE/Contents/Frameworks/Sentry.framework"
else
    echo "    WARNING: Sentry.framework not found, Sentry may be statically linked"
fi

# Copy other resources
echo "    Copying resources..."
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

# Create app icon from Oximy-rounded.png BEFORE signing (critical!)
echo "[5/7] Creating app icon..."
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

# Code signing (requires Developer ID)
echo "[6/7] Code signing..."
if [ -n "$DEVELOPER_ID" ]; then
    echo "    Signing with: $DEVELOPER_ID"
    ENTITLEMENTS_FILE="$PROJECT_DIR/OximyMac.entitlements"

    # Sign embedded frameworks first (required for notarization)
    # Sparkle framework
    if [ -d "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework" ]; then
        echo "    Signing Sparkle.framework..."
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework/Versions/B/XPCServices/Installer.xpc"
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework/Versions/B/XPCServices/Downloader.xpc"
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework/Versions/B/Autoupdate"
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework/Versions/B/Updater.app"
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
    fi

    # Sentry framework
    if [ -d "$APP_BUNDLE/Contents/Frameworks/Sentry.framework" ]; then
        echo "    Signing Sentry.framework..."
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/Frameworks/Sentry.framework"
    fi

    # Sign any other frameworks
    find "$APP_BUNDLE/Contents/Frameworks" -name "*.framework" -type d 2>/dev/null | while read framework; do
        echo "    Signing $(basename "$framework")..."
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$framework" 2>/dev/null || true
    done

    # Sign any dylibs
    find "$APP_BUNDLE" -name "*.dylib" -type f 2>/dev/null | while read dylib; do
        echo "    Signing $(basename "$dylib")..."
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$dylib" 2>/dev/null || true
    done

    # Sign bundled Python if present
    if [ -d "$APP_BUNDLE/Contents/Resources/python-embed" ]; then
        echo "    Signing bundled Python..."
        find "$APP_BUNDLE/Contents/Resources/python-embed" -type f \( -name "*.so" -o -name "*.dylib" -o -perm +111 \) 2>/dev/null | while read binary; do
            codesign --force --options runtime --timestamp \
                --sign "$DEVELOPER_ID" \
                "$binary" 2>/dev/null || true
        done
    fi

    # Sign the main binary (with entitlements)
    echo "    Signing main binary..."
    if [ -f "$ENTITLEMENTS_FILE" ]; then
        codesign --force --options runtime --timestamp \
            --entitlements "$ENTITLEMENTS_FILE" \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
    else
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
    fi

    # Finally sign the main app bundle (with entitlements)
    echo "    Signing main app bundle..."
    if [ -f "$ENTITLEMENTS_FILE" ]; then
        echo "    Using entitlements: $ENTITLEMENTS_FILE"
        codesign --force --options runtime --timestamp \
            --entitlements "$ENTITLEMENTS_FILE" \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE"
    else
        echo "    WARNING: Entitlements file not found, signing without entitlements"
        codesign --force --options runtime --timestamp \
            --sign "$DEVELOPER_ID" \
            "$APP_BUNDLE"
    fi

    echo "    Code signing complete"

    # Verify signature
    echo "    Verifying signature..."
    if codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE" 2>&1; then
        echo "    ✓ Signature verification passed"
    else
        echo "    ✗ Signature verification FAILED"
        exit 1
    fi
else
    echo "    STUB: Skipping code signing (no DEVELOPER_ID set)"
    echo "    To sign, run: DEVELOPER_ID='Developer ID Application: Your Name' $0"
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
    echo "    Found create-dmg at: $(which create-dmg)"
    cd "$BUILD_DIR"
    # Remove existing DMG if present
    rm -f "$DMG_PATH" 2>/dev/null || true
    rm -f "$APP_NAME $VERSION.dmg" 2>/dev/null || true

    # create-dmg automatically handles Applications symlink and styling
    # Use --no-code-sign since the app is already signed, and DMG will be signed during notarization
    if create-dmg "$APP_BUNDLE" "$BUILD_DIR" --overwrite --no-code-sign 2>&1; then
        echo "    create-dmg succeeded"
    else
        echo "    create-dmg exited with non-zero status (may still have created DMG)"
    fi

    # create-dmg names files as "AppName VERSION.dmg", rename to our format
    if [ -f "$BUILD_DIR/$APP_NAME $VERSION.dmg" ]; then
        mv "$BUILD_DIR/$APP_NAME $VERSION.dmg" "$DMG_PATH"
        echo "    DMG created: $DMG_PATH"
    else
        echo "    ERROR: Expected DMG not found at $BUILD_DIR/$APP_NAME $VERSION.dmg"
        echo "    Falling back to hdiutil..."
        hdiutil create -volname "$APP_NAME" \
            -srcfolder "$APP_BUNDLE" \
            -ov -format UDZO \
            "$DMG_PATH"
    fi
else
    echo "    WARNING: create-dmg not found, falling back to basic DMG creation"
    # Fallback: simple DMG without styling
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$APP_BUNDLE" \
        -ov -format UDZO \
        "$DMG_PATH"
fi

# Step 8: Sign for Sparkle updates and generate appcast
echo "[8/8] Sparkle update signing..."
if [ -n "$SPARKLE_PRIVATE_KEY" ] && [ -f "$DMG_PATH" ]; then
    # Try to find Sparkle's sign_update tool (check artifacts first, then checkouts)
    SPARKLE_SIGN="$PROJECT_DIR/.build/artifacts/sparkle/Sparkle/bin/sign_update"
    if [ ! -f "$SPARKLE_SIGN" ]; then
        SPARKLE_SIGN="$PROJECT_DIR/.build/checkouts/Sparkle/sign_update"
    fi

    if [ -f "$SPARKLE_SIGN" ]; then
        echo "    Signing DMG with Sparkle EdDSA key..."

        # Generate EdDSA signature
        SIGNATURE=$("$SPARKLE_SIGN" "$DMG_PATH" -s "$SPARKLE_PRIVATE_KEY" 2>/dev/null | grep "sparkle:edSignature" | cut -d'"' -f2 || echo "")

        if [ -n "$SIGNATURE" ]; then
            echo "    EdDSA Signature: ${SIGNATURE:0:20}..."

            # Get file size and generate date
            DMG_SIZE=$(stat -f%z "$DMG_PATH")
            PUB_DATE=$(date -u +"%a, %d %b %Y %H:%M:%S +0000")

            # Generate appcast.xml
            cat > "$BUILD_DIR/appcast.xml" << APPCAST_EOF
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <title>Oximy Updates</title>
    <link>https://github.com/OximyHQ/mitmproxy/releases</link>
    <description>Updates for Oximy macOS</description>
    <language>en</language>
    <item>
      <title>Version $VERSION</title>
      <pubDate>$PUB_DATE</pubDate>
      <sparkle:version>$VERSION</sparkle:version>
      <sparkle:shortVersionString>$VERSION</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>13.0</sparkle:minimumSystemVersion>
      <enclosure
        url="https://github.com/OximyHQ/mitmproxy/releases/download/oximy-v$VERSION/$DMG_NAME"
        length="$DMG_SIZE"
        type="application/octet-stream"
        sparkle:edSignature="$SIGNATURE"
      />
      <sparkle:releaseNotesLink>
        https://github.com/OximyHQ/mitmproxy/releases/tag/oximy-v$VERSION
      </sparkle:releaseNotesLink>
    </item>
  </channel>
</rss>
APPCAST_EOF
            echo "    Generated appcast.xml"
        else
            echo "    WARNING: Failed to generate EdDSA signature"
        fi
    else
        echo "    WARNING: Sparkle sign_update tool not found at $SPARKLE_SIGN"
        echo "    Run 'swift build' first to fetch Sparkle package"
    fi
else
    if [ -z "$SPARKLE_PRIVATE_KEY" ]; then
        echo "    STUB: Skipping Sparkle signing (no SPARKLE_PRIVATE_KEY set)"
        echo "    To sign for updates:"
        echo "    1. Generate keys: .build/checkouts/Sparkle/bin/generate_keys"
        echo "    2. Set SPARKLE_PRIVATE_KEY environment variable"
        echo "    3. Set SPARKLE_PUBLIC_KEY for Info.plist"
    fi
fi

echo ""
echo "=== Build Complete ==="
echo ""
echo "App Bundle: $APP_BUNDLE"
echo "DMG:        $DMG_PATH"
if [ -f "$BUILD_DIR/appcast.xml" ]; then
    echo "Appcast:    $BUILD_DIR/appcast.xml"
fi
echo ""

if [ -z "$DEVELOPER_ID" ]; then
    echo "NOTE: App is unsigned. For distribution:"
    echo "  1. Set DEVELOPER_ID environment variable"
    echo "  2. Run this script again"
    echo "  3. Notarize with: xcrun notarytool submit $DMG_PATH"
fi

if [ -z "$SPARKLE_PRIVATE_KEY" ]; then
    echo ""
    echo "NOTE: Update signing not configured. For auto-updates:"
    echo "  1. Generate keys: swift build && .build/checkouts/Sparkle/bin/generate_keys"
    echo "  2. Set SPARKLE_PRIVATE_KEY (keep secret!)"
    echo "  3. Set SPARKLE_PUBLIC_KEY (add to Info.plist)"
fi

echo ""
echo "To test locally:"
echo "  open $APP_BUNDLE"
echo ""
