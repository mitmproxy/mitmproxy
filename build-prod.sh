#!/bin/bash
# =============================================================================
# Oximy Production Build Script
# =============================================================================
# Usage:
#   ./build-prod.sh mac --version 1.0.0
#   ./build-prod.sh windows --version 1.0.0
#
# Required environment variables for macOS:
#   DEVELOPER_ID        - "Developer ID Application: Your Name (TEAMID)"
#   APPLE_ID            - Your Apple ID email for notarization
#   APPLE_APP_PASSWORD  - App-specific password for notarization
#   TEAM_ID             - Your Apple Team ID
#   SENTRY_DSN          - Sentry DSN for crash reporting (optional)
#   SENTRY_AUTH_TOKEN   - Sentry auth token for dSYM upload (optional)
#   SENTRY_ORG          - Sentry organization slug (optional)
#   SENTRY_PROJECT      - Sentry project slug (optional)
#
# You can put these in a .env.local file and source it before running:
#   source .env.local && ./build-prod.sh mac --version 1.0.0
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.0.0"
PLATFORM=""
SKIP_PYTHON_BUILD=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${CYAN}=== $1 ===${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

usage() {
    echo "Oximy Production Build Script"
    echo ""
    echo "Usage: $0 <platform> [options]"
    echo ""
    echo "Platforms:"
    echo "  mac       Build macOS app (DMG with notarization)"
    echo "  windows   Build Windows app (Velopack release)"
    echo ""
    echo "Options:"
    echo "  --version <ver>     Version number (default: 1.0.0)"
    echo "  --skip-python       Skip Python embed build (use existing)"
    echo "  --help              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 mac --version 1.2.0"
    echo "  $0 windows --version 1.2.0"
    echo ""
    echo "Environment variables (macOS):"
    echo "  DEVELOPER_ID        Code signing identity"
    echo "  APPLE_ID            Apple ID for notarization"
    echo "  APPLE_APP_PASSWORD  App-specific password"
    echo "  TEAM_ID             Apple Team ID"
    echo ""
    echo "Tip: Create a .env.local file with your credentials:"
    echo "  export DEVELOPER_ID=\"Developer ID Application: ...\""
    echo "  export APPLE_ID=\"your@email.com\""
    echo "  export APPLE_APP_PASSWORD=\"xxxx-xxxx-xxxx-xxxx\""
    echo "  export TEAM_ID=\"XXXXXXXXXX\""
    exit 1
}

# Parse arguments
if [ $# -lt 1 ]; then
    usage
fi

PLATFORM="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --skip-python)
            SKIP_PYTHON_BUILD=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate platform
if [ "$PLATFORM" != "mac" ] && [ "$PLATFORM" != "windows" ]; then
    echo "Invalid platform: $PLATFORM"
    usage
fi

# =============================================================================
# macOS Build
# =============================================================================
build_mac() {
    print_header "Oximy macOS Production Build"
    echo "Version: $VERSION"
    echo "Platform: macOS (Universal Binary)"
    echo ""

    # Check required environment variables
    local missing_vars=()
    [ -z "$DEVELOPER_ID" ] && missing_vars+=("DEVELOPER_ID")
    [ -z "$APPLE_ID" ] && missing_vars+=("APPLE_ID")
    [ -z "$APPLE_APP_PASSWORD" ] && missing_vars+=("APPLE_APP_PASSWORD")
    [ -z "$TEAM_ID" ] && missing_vars+=("TEAM_ID")

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Set these variables or create a .env.local file:"
        echo "  export DEVELOPER_ID=\"Developer ID Application: Your Name (TEAMID)\""
        echo "  export APPLE_ID=\"your@email.com\""
        echo "  export APPLE_APP_PASSWORD=\"xxxx-xxxx-xxxx-xxxx\""
        echo "  export TEAM_ID=\"XXXXXXXXXX\""
        exit 1
    fi

    print_success "All required credentials found"
    echo "  DEVELOPER_ID: ${DEVELOPER_ID:0:50}..."
    echo "  APPLE_ID: $APPLE_ID"
    echo "  TEAM_ID: $TEAM_ID"

    cd "$SCRIPT_DIR/OximyMac"

    # Step 1: Create Secrets.swift
    print_header "Step 1/9: Creating Secrets.swift"
    if [ -n "$SENTRY_DSN" ]; then
        cat > App/Secrets.swift << EOF
import Foundation

enum Secrets {
    static let sentryDSN: String? = "$SENTRY_DSN"
}
EOF
        print_success "Created Secrets.swift with Sentry DSN"
    else
        cp App/Secrets.example.swift App/Secrets.swift
        print_warning "Created Secrets.swift from example (no SENTRY_DSN)"
    fi

    # Step 2: Build Python embed
    print_header "Step 2/9: Building Python Embed"
    if [ "$SKIP_PYTHON_BUILD" = true ] && [ -d "Resources/python-embed" ]; then
        print_warning "Skipping Python build (using existing)"
    else
        echo "Building Universal Python embed (this takes a few minutes)..."
        chmod +x Scripts/build-python-embed.sh
        ./Scripts/build-python-embed.sh
        print_success "Python embed built"
    fi

    # Step 3: Sync addon
    print_header "Step 3/9: Syncing Addon"
    make sync
    print_success "Addon synced"

    # Step 4: Fetch Swift dependencies
    print_header "Step 4/9: Fetching Swift Dependencies"
    swift package resolve
    swift build --target OximyMac 2>/dev/null || true
    print_success "Dependencies fetched"

    # Step 5: Build release
    print_header "Step 5/9: Building Release"
    export VERSION
    export DEVELOPER_ID
    chmod +x Scripts/build-release.sh
    ./Scripts/build-release.sh
    print_success "App bundle built and signed"

    # Step 6: Notarize
    print_header "Step 6/9: Notarizing App"
    cd build

    echo "Creating zip for notarization..."
    ditto -c -k --keepParent "Oximy.app" "Oximy.zip"

    echo "Submitting for notarization (this may take a few minutes)..."
    SUBMIT_OUTPUT=$(xcrun notarytool submit "Oximy.zip" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --team-id "$TEAM_ID" \
        --wait 2>&1) || true

    echo "$SUBMIT_OUTPUT"

    # Extract submission ID for potential log retrieval
    SUBMISSION_ID=$(echo "$SUBMIT_OUTPUT" | grep -o 'id: [a-f0-9-]*' | head -1 | cut -d' ' -f2)

    if echo "$SUBMIT_OUTPUT" | grep -q "status: Accepted"; then
        print_success "Notarization succeeded!"

        echo "Stapling notarization ticket..."
        xcrun stapler staple "Oximy.app"
        print_success "Notarization ticket stapled"
    else
        print_error "Notarization failed!"
        if [ -n "$SUBMISSION_ID" ]; then
            echo "Fetching notarization log..."
            xcrun notarytool log "$SUBMISSION_ID" \
                --apple-id "$APPLE_ID" \
                --password "$APPLE_APP_PASSWORD" \
                --team-id "$TEAM_ID" \
                notarization-log.json 2>/dev/null || true
            [ -f notarization-log.json ] && cat notarization-log.json
        fi
        exit 1
    fi

    rm -f "Oximy.zip"

    # Step 7: Verify
    print_header "Step 7/9: Verifying Notarization"
    echo "Verifying code signature..."
    codesign -dvv Oximy.app
    echo ""
    echo "Verifying notarization (spctl)..."
    spctl -a -v Oximy.app
    echo ""
    echo "Verifying staple..."
    xcrun stapler validate Oximy.app
    print_success "All verifications passed"

    # Step 7.5: Upload dSYMs to Sentry (optional)
    if [ -n "$SENTRY_AUTH_TOKEN" ] && [ -n "$SENTRY_ORG" ] && [ -n "$SENTRY_PROJECT" ]; then
        print_header "Uploading dSYMs to Sentry"
        if command -v sentry-cli &> /dev/null; then
            DSYM_PATH="$SCRIPT_DIR/OximyMac/.build"
            echo "Searching for dSYMs in: $DSYM_PATH"
            sentry-cli debug-files upload --include-sources \
                --org "$SENTRY_ORG" \
                --project "$SENTRY_PROJECT" \
                "$DSYM_PATH"
            print_success "dSYMs uploaded to Sentry"
        else
            print_warning "sentry-cli not found — install with: brew install getsentry/tools/sentry-cli"
        fi
    else
        print_warning "Skipping dSYM upload (SENTRY_AUTH_TOKEN, SENTRY_ORG, or SENTRY_PROJECT not set)"
    fi

    # Step 8: Create DMG with volume icon + Applications symlink
    print_header "Step 8/9: Creating DMG"
    DMG_NAME="Oximy-$VERSION.dmg"
    DMG_TEMP="Oximy-temp.dmg"
    VOLUME_NAME="Oximy"
    VOLUME_ICON="$SCRIPT_DIR/OximyMac/Resources/Oximy-dmg.png"
    APP_ICNS="Oximy.app/Contents/Resources/AppIcon.icns"

    rm -f "$DMG_NAME" "$DMG_TEMP" 2>/dev/null || true

    # Create a read-write DMG, mount it, add contents + volume icon, then convert
    # Calculate required size: app size + 50MB headroom for icons, symlinks, metadata
    APP_SIZE_KB=$(du -sk "Oximy.app" | awk '{print $1}')
    DMG_SIZE_MB=$(( (APP_SIZE_KB / 1024) + 50 ))
    echo "Creating read-write DMG (${DMG_SIZE_MB}MB for ${APP_SIZE_KB}KB app)..."
    hdiutil create -size "${DMG_SIZE_MB}m" -fs HFS+ -volname "$VOLUME_NAME" -ov "$DMG_TEMP"

    echo "Mounting DMG..."
    MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" -readwrite -noverify | grep "/Volumes/$VOLUME_NAME" | awk '{print $NF}')
    # Handle volume names with spaces in mount path
    if [ -z "$MOUNT_DIR" ]; then
        MOUNT_DIR="/Volumes/$VOLUME_NAME"
    fi
    echo "    Mounted at: $MOUNT_DIR"

    echo "Copying app bundle..."
    cp -R "Oximy.app" "$MOUNT_DIR/"

    echo "Creating Applications symlink..."
    ln -s /Applications "$MOUNT_DIR/Applications"

    # Set the volume icon
    echo "Setting volume icon..."
    if [ -f "$APP_ICNS" ]; then
        # Use the app's .icns directly as the volume icon
        cp "$APP_ICNS" "$MOUNT_DIR/.VolumeIcon.icns"
        SetFile -a C "$MOUNT_DIR" 2>/dev/null || true
        print_success "Volume icon set from AppIcon.icns"
    elif [ -f "$VOLUME_ICON" ]; then
        # Convert PNG to icns for volume icon
        TEMP_ICONSET="$BUILD_DIR/VolumeIcon.iconset"
        mkdir -p "$TEMP_ICONSET"
        sips -z 512 512 "$VOLUME_ICON" --out "$TEMP_ICONSET/icon_256x256@2x.png" 2>/dev/null
        sips -z 256 256 "$VOLUME_ICON" --out "$TEMP_ICONSET/icon_256x256.png" 2>/dev/null
        sips -z 128 128 "$VOLUME_ICON" --out "$TEMP_ICONSET/icon_128x128.png" 2>/dev/null
        iconutil -c icns "$TEMP_ICONSET" -o "$MOUNT_DIR/.VolumeIcon.icns" 2>/dev/null || true
        rm -rf "$TEMP_ICONSET"
        SetFile -a C "$MOUNT_DIR" 2>/dev/null || true
        print_success "Volume icon set from Oximy-dmg.png"
    else
        print_warning "No icon source found, DMG will have default icon"
    fi

    # Set Finder window layout (icon size, background, positions)
    echo "Configuring Finder layout..."
    echo '
        tell application "Finder"
            tell disk "'$VOLUME_NAME'"
                open
                set current view of container window to icon view
                set toolbar visible of container window to false
                set statusbar visible of container window to false
                set the bounds of container window to {100, 100, 640, 400}
                set viewOptions to the icon view options of container window
                set arrangement of viewOptions to not arranged
                set icon size of viewOptions to 80
                set position of item "Oximy.app" of container window to {150, 150}
                set position of item "Applications" of container window to {390, 150}
                close
            end tell
        end tell
    ' | osascript 2>/dev/null || true

    # Give Finder time to write .DS_Store
    sync
    sleep 1

    echo "Detaching DMG..."
    hdiutil detach "$MOUNT_DIR" -quiet 2>/dev/null || hdiutil detach "$MOUNT_DIR" -force 2>/dev/null || true

    echo "Converting to compressed read-only DMG..."
    hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_NAME"
    rm -f "$DMG_TEMP"

    print_success "DMG created: $DMG_NAME"
    ls -lh "$DMG_NAME"

    # Step 9: Create PKG installer (for in-app updates — no drag-to-install)
    print_header "Step 9/9: Creating PKG Installer"
    PKG_NAME="Oximy-$VERSION.pkg"
    PKG_STAGING="pkg-staging"
    PKG_ROOT="$PKG_STAGING/root"
    PKG_SCRIPTS_DIR="$PKG_STAGING/scripts"
    BUNDLE_ID="com.oximy.mac"
    INSTALLER_DIR="$SCRIPT_DIR/OximyMac/Installer"

    rm -rf "$PKG_STAGING"
    mkdir -p "$PKG_ROOT/Applications"
    mkdir -p "$PKG_SCRIPTS_DIR"

    echo "Copying notarized app to PKG staging..."
    cp -R "Oximy.app" "$PKG_ROOT/Applications/"

    echo "Copying installer scripts..."
    cp "$INSTALLER_DIR/Scripts/preinstall" "$PKG_SCRIPTS_DIR/"
    cp "$INSTALLER_DIR/Scripts/postinstall" "$PKG_SCRIPTS_DIR/"
    chmod +x "$PKG_SCRIPTS_DIR/"*

    echo "Building component package..."
    pkgbuild \
        --root "$PKG_ROOT" \
        --install-location "/" \
        --scripts "$PKG_SCRIPTS_DIR" \
        --identifier "$BUNDLE_ID" \
        --version "$VERSION" \
        --ownership recommended \
        "OximyComponent.pkg"

    echo "Building distribution package..."
    cat > "distribution.xml" << DISTEOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>Oximy</title>
    <organization>com.oximy</organization>
    <options customize="never" require-scripts="false" hostArchitectures="x86_64,arm64"/>
    <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
    <installation-check script="InstallationCheck()"/>
    <script>
    function InstallationCheck() {
        if(system.compareVersions(system.version.ProductVersion, '13.0') >= 0) {
            return true;
        }
        my.result.title = 'macOS 13.0 Required';
        my.result.message = 'Oximy requires macOS 13.0 (Ventura) or later.';
        my.result.type = 'Fatal';
        return false;
    }
    </script>
    <choices-outline>
        <line choice="default"/>
    </choices-outline>
    <choice id="default" title="Oximy">
        <pkg-ref id="$BUNDLE_ID"/>
    </choice>
    <pkg-ref id="$BUNDLE_ID" version="$VERSION">OximyComponent.pkg</pkg-ref>
</installer-gui-script>
DISTEOF

    UNSIGNED_PKG="Oximy-$VERSION-unsigned.pkg"
    productbuild \
        --distribution "distribution.xml" \
        --package-path "." \
        --version "$VERSION" \
        "$UNSIGNED_PKG"

    # Sign the PKG (requires Developer ID Installer certificate)
    if [ -n "$INSTALLER_CERT" ]; then
        echo "Signing PKG with: $INSTALLER_CERT"
        productsign \
            --sign "$INSTALLER_CERT" \
            "$UNSIGNED_PKG" \
            "$PKG_NAME"
        rm "$UNSIGNED_PKG"
        print_success "PKG signed"
    else
        mv "$UNSIGNED_PKG" "$PKG_NAME"
        print_warning "PKG unsigned (no INSTALLER_CERT set)"
    fi

    # Notarize the PKG itself (separate from app notarization)
    if [ -n "$APPLE_ID" ] && [ -n "$APPLE_APP_PASSWORD" ] && [ -n "$TEAM_ID" ]; then
        echo "Submitting PKG for notarization..."
        PKG_SUBMIT=$(xcrun notarytool submit "$PKG_NAME" \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_APP_PASSWORD" \
            --team-id "$TEAM_ID" \
            --wait 2>&1) || true

        echo "$PKG_SUBMIT"

        if echo "$PKG_SUBMIT" | grep -q "status: Accepted"; then
            xcrun stapler staple "$PKG_NAME"
            print_success "PKG notarized and stapled"
        else
            print_warning "PKG notarization failed — PKG may trigger Gatekeeper warnings"
        fi
    else
        print_warning "Skipping PKG notarization (credentials not set)"
    fi

    # Cleanup staging
    rm -rf "$PKG_STAGING" "OximyComponent.pkg" "distribution.xml"

    print_success "PKG created: $PKG_NAME"
    ls -lh "$PKG_NAME"

    # Done!
    print_header "macOS Build Complete!"
    echo ""
    echo "Output files in: $SCRIPT_DIR/OximyMac/build/"
    echo ""
    ls -lh "$SCRIPT_DIR/OximyMac/build/"*.dmg "$SCRIPT_DIR/OximyMac/build/"*.pkg 2>/dev/null || true
    echo ""
    echo "To test: open $SCRIPT_DIR/OximyMac/build/Oximy.app"
    echo ""
    echo "To release:"
    echo "  1. Create GitHub release tagged 'oximy-v$VERSION'"
    echo "  2. Upload: Oximy-$VERSION.dmg + Oximy-$VERSION.pkg"
}

# =============================================================================
# Windows Build
# =============================================================================
build_windows() {
    print_header "Oximy Windows Production Build"
    echo "Version: $VERSION"
    echo "Platform: Windows x64"
    echo ""

    # Check if we're on Windows or have PowerShell
    if command -v pwsh &> /dev/null; then
        POWERSHELL="pwsh"
    elif command -v powershell &> /dev/null; then
        POWERSHELL="powershell"
    else
        print_error "PowerShell not found!"
        echo "Windows builds require PowerShell."
        echo ""
        echo "On macOS/Linux, you can install PowerShell:"
        echo "  brew install powershell/tap/powershell"
        echo ""
        echo "Or run this script on Windows directly."
        exit 1
    fi

    # Validate SemVer format
    if ! echo "$VERSION" | grep -qE '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)?$'; then
        print_error "Invalid version format: $VERSION"
        echo "Version must be SemVer2 compliant (e.g., 1.0.0, 1.2.3-beta.1)"
        exit 1
    fi

    cd "$SCRIPT_DIR/OximyWindows"

    # Step 0: Sentry DSN is hardcoded in SentryService.cs (Secrets partial class).
    # The SENTRY_DSN env var can still override it at runtime via App.xaml.cs.
    # No Secrets.cs generation needed — avoids duplicate property compilation error.
    print_header "Step 0: Sentry DSN (hardcoded)"
    print_success "Sentry DSN is hardcoded in SentryService.cs — no Secrets.cs needed"

    # Update version in project files
    print_header "Step 1/3: Updating Version"

    # Update csproj
    if [ -f "src/OximyWindows/OximyWindows.csproj" ]; then
        sed -i.bak "s|<Version>.*</Version>|<Version>$VERSION</Version>|g" "src/OximyWindows/OximyWindows.csproj"
        rm -f "src/OximyWindows/OximyWindows.csproj.bak"
        print_success "Updated OximyWindows.csproj"
    fi

    # Update Constants.cs
    if [ -f "src/OximyWindows/Constants.cs" ]; then
        sed -i.bak "s|Version = \".*\"|Version = \"$VERSION\"|g" "src/OximyWindows/Constants.cs"
        rm -f "src/OximyWindows/Constants.cs.bak"
        print_success "Updated Constants.cs"
    fi

    # Run build script
    print_header "Step 2/3: Building with Inno Setup"

    cd scripts
    $POWERSHELL -ExecutionPolicy Bypass -File build.ps1 -Release -Clean -CreateInstaller -Version "$VERSION"

    if [ $? -ne 0 ]; then
        print_error "Build failed!"
        exit 1
    fi

    print_success "Build complete"

    # Summary
    print_header "Step 3/3: Build Summary"
    cd "$SCRIPT_DIR/OximyWindows"

    echo ""
    echo "Output files in: $SCRIPT_DIR/OximyWindows/releases/"
    echo ""
    ls -lh releases/ 2>/dev/null || true
    echo ""
    echo "To release:"
    echo "  1. Create GitHub release tagged 'oximy-v$VERSION'"
    echo "  2. Upload all files from releases/ directory"

    print_header "Windows Build Complete!"
}

# =============================================================================
# Main
# =============================================================================

print_header "Oximy Production Build"
echo "Platform: $PLATFORM"
echo "Version:  $VERSION"
echo "Date:     $(date)"

case $PLATFORM in
    mac)
        build_mac
        ;;
    windows)
        build_windows
        ;;
esac
