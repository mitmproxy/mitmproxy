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

# Build Universal Binary by default (supports both Apple Silicon and Intel Macs)
BUILD_UNIVERSAL="${BUILD_UNIVERSAL:-true}"
ARCH=$(uname -m)

echo "=== Oximy Build ==="
echo "Version: $VERSION"
echo "Configuration: $BUILD_CONFIG"
echo "Universal Binary: $BUILD_UNIVERSAL"
echo "Host Architecture: $ARCH"
echo "Project: $PROJECT_DIR"
echo ""

# Sync addon files (converts imports for standalone use)
echo "[1/8] Syncing addon files..."
"$SCRIPT_DIR/sync-addon.sh"

# Clean previous build
echo "[2/8] Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build
echo "[3/8] Building in $BUILD_CONFIG mode..."
cd "$PROJECT_DIR"

if [ "$BUILD_UNIVERSAL" = "true" ]; then
    echo "    Building Universal Binary (arm64 + x86_64)..."
    swift build -c "$BUILD_CONFIG" --arch arm64 --arch x86_64
else
    echo "    Building for host architecture only ($ARCH)..."
    swift build -c "$BUILD_CONFIG"
fi

# Create app bundle structure
echo "[4/8] Creating app bundle..."
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy binary - check multiple possible locations
# Universal builds go to .build/apple/Products/Release/ or similar
BINARY_PATH=""
for path in \
    ".build/apple/Products/Release/OximyMac" \
    ".build/apple/Products/Debug/OximyMac" \
    ".build/arm64-apple-macosx/$BUILD_CONFIG/OximyMac" \
    ".build/x86_64-apple-macosx/$BUILD_CONFIG/OximyMac" \
    ".build/$BUILD_CONFIG/OximyMac"; do
    if [ -f "$path" ]; then
        BINARY_PATH="$path"
        break
    fi
done
if [ -z "$BINARY_PATH" ]; then
    echo "ERROR: Binary not found. Searched locations:"
    echo "  - .build/apple/Products/Release/OximyMac"
    echo "  - .build/apple/Products/Debug/OximyMac"
    echo "  - .build/arm64-apple-macosx/$BUILD_CONFIG/OximyMac"
    echo "  - .build/x86_64-apple-macosx/$BUILD_CONFIG/OximyMac"
    echo "  - .build/$BUILD_CONFIG/OximyMac"
    echo ""
    echo "Available in .build:"
    find .build -name "OximyMac" -type f 2>/dev/null | head -10
    exit 1
fi

# Verify architecture
echo "    Binary: $BINARY_PATH"
file "$BINARY_PATH"

cp "$BINARY_PATH" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Fix rpath so the binary can find frameworks in Contents/Frameworks
echo "    Fixing rpath for framework loading..."
install_name_tool -add_rpath "@executable_path/../Frameworks" "$APP_BUNDLE/Contents/MacOS/$APP_NAME" 2>/dev/null || true

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

# Copy frameworks (Sentry)
echo "[5/8] Copying frameworks..."
mkdir -p "$APP_BUNDLE/Contents/Frameworks"

# Copy Sentry.framework - check multiple possible locations
SENTRY_FRAMEWORK=""
for path in \
    "$PROJECT_DIR/.build/apple/Products/Release/Sentry.framework" \
    "$PROJECT_DIR/.build/apple/Products/Debug/Sentry.framework" \
    "$PROJECT_DIR/.build/arm64-apple-macosx/$BUILD_CONFIG/Sentry.framework" \
    "$PROJECT_DIR/.build/$BUILD_CONFIG/Sentry.framework" \
    "$PROJECT_DIR/.build/artifacts/sentry-cocoa/Sentry-Dynamic/Sentry-Dynamic.xcframework/macos-arm64_x86_64/Sentry.framework"; do
    if [ -d "$path" ]; then
        SENTRY_FRAMEWORK="$path"
        break
    fi
done
if [ -d "$SENTRY_FRAMEWORK" ]; then
    echo "    Copying Sentry.framework from $SENTRY_FRAMEWORK..."
    cp -R "$SENTRY_FRAMEWORK" "$APP_BUNDLE/Contents/Frameworks/Sentry.framework"
else
    echo "    WARNING: Sentry.framework not found, Sentry may be statically linked"
fi

# Copy other resources (excluding items that are copied explicitly below)
echo "    Copying resources..."
if [ -d "$PROJECT_DIR/Resources" ]; then
    # Copy resources except python-embed and oximy-addon which are handled separately
    for item in "$PROJECT_DIR/Resources/"*; do
        basename_item=$(basename "$item")
        if [ "$basename_item" != "python-embed" ] && [ "$basename_item" != "oximy-addon" ]; then
            cp -R "$item" "$APP_BUNDLE/Contents/Resources/" 2>/dev/null || true
        fi
    done
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

# Copy addon from synced location (with converted imports for standalone use)
# The source of truth is mitmproxy/addons/oximy/, but sync-addon.sh converts
# absolute imports to relative imports for standalone bundled Python use
ADDON_SRC="$PROJECT_DIR/Resources/oximy-addon"
if [ -d "$ADDON_SRC" ]; then
    cp -R "$ADDON_SRC" "$APP_BUNDLE/Contents/Resources/oximy-addon"
    echo "    Copied addon from: $ADDON_SRC (synced with relative imports)"
else
    echo "ERROR: Synced addon not found at $ADDON_SRC"
    echo "       Run 'make sync' first to sync and convert addon imports"
    exit 1
fi

# Create app icon BEFORE signing (critical!)
# IMPORTANT: Use SQUARE icon - macOS automatically applies rounded corners to app icons
# Using pre-rounded icons causes double-rounding and bleed issues
echo "[6/8] Creating app icon..."
ICON_SOURCE="$PROJECT_DIR/Resources/Assets.xcassets/AppIcon.appiconset/1024.png"
# Fall back to Oximy.png if 1024.png doesn't exist
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
    echo "    Created AppIcon.icns from $ICON_SOURCE"
else
    echo "    WARNING: Oximy.png not found, skipping icon generation"
fi

# Code signing (requires Developer ID)
echo "[7/8] Code signing..."
if [ -n "$DEVELOPER_ID" ]; then
    echo "    Signing with: $DEVELOPER_ID"
    ENTITLEMENTS_FILE="$PROJECT_DIR/OximyMac.entitlements"

    # Sign embedded frameworks first (required for notarization)
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
    # IMPORTANT: All binaries must be signed for notarization, including .so files.
    # Python extensions need special entitlements to work when signed with hardened runtime.
    if [ -d "$APP_BUNDLE/Contents/Resources/python-embed" ]; then
        echo "    Signing bundled Python binaries..."
        # Sign all Mach-O binaries (.so, .dylib, executables) with entitlements
        find "$APP_BUNDLE/Contents/Resources/python-embed" -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read binary; do
            codesign --force --options runtime --timestamp \
                --entitlements "$ENTITLEMENTS_FILE" \
                --sign "$DEVELOPER_ID" \
                "$binary" 2>/dev/null || true
        done
        # Sign executables
        find "$APP_BUNDLE/Contents/Resources/python-embed" -type f -perm +111 ! -name "*.so" ! -name "*.dylib" 2>/dev/null | while read binary; do
            if file "$binary" | grep -q "Mach-O"; then
                codesign --force --options runtime --timestamp \
                    --entitlements "$ENTITLEMENTS_FILE" \
                    --sign "$DEVELOPER_ID" \
                    "$binary" 2>/dev/null || true
            fi
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

# Skip DMG creation here - it will be done AFTER notarization in CI
# This ensures the app bundle signature is not invalidated by DMG creation
echo "[8/8] Skipping DMG creation (done after notarization in CI)..."
DMG_NAME="$APP_NAME-$VERSION.dmg"
DMG_PATH="$BUILD_DIR/$DMG_NAME"
echo "    App bundle ready for notarization: $APP_BUNDLE"
echo "    DMG will be created after stapling notarization ticket"

echo ""
echo "=== Build Complete ==="
echo ""
echo "App Bundle: $APP_BUNDLE"
echo ""

if [ -z "$DEVELOPER_ID" ]; then
    echo "NOTE: App is unsigned. For distribution:"
    echo "  1. Set DEVELOPER_ID environment variable"
    echo "  2. Run this script again"
    echo "  3. Notarize the app bundle"
    echo "  4. Staple the notarization ticket"
    echo "  5. Create DMG from stapled app"
fi

echo ""
echo "To test locally:"
echo "  open $APP_BUNDLE"
echo ""
