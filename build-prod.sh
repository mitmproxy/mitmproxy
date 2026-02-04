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
    print_header "Step 1/8: Creating Secrets.swift"
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
    print_header "Step 2/8: Building Python Embed"
    if [ "$SKIP_PYTHON_BUILD" = true ] && [ -d "Resources/python-embed" ]; then
        print_warning "Skipping Python build (using existing)"
    else
        echo "Building Universal Python embed (this takes a few minutes)..."
        chmod +x Scripts/build-python-embed.sh
        ./Scripts/build-python-embed.sh
        print_success "Python embed built"
    fi

    # Step 3: Sync addon
    print_header "Step 3/8: Syncing Addon"
    make sync
    print_success "Addon synced"

    # Step 4: Fetch Swift dependencies
    print_header "Step 4/8: Fetching Swift Dependencies"
    swift package resolve
    swift build --target OximyMac 2>/dev/null || true
    print_success "Dependencies fetched"

    # Step 5: Build release
    print_header "Step 5/8: Building Release"
    export VERSION
    export DEVELOPER_ID
    chmod +x Scripts/build-release.sh
    ./Scripts/build-release.sh
    print_success "App bundle built and signed"

    # Step 6: Notarize
    print_header "Step 6/8: Notarizing App"
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
    print_header "Step 7/8: Verifying Notarization"
    echo "Verifying code signature..."
    codesign -dvv Oximy.app
    echo ""
    echo "Verifying notarization (spctl)..."
    spctl -a -v Oximy.app
    echo ""
    echo "Verifying staple..."
    xcrun stapler validate Oximy.app
    print_success "All verifications passed"

    # Step 8: Create DMG
    print_header "Step 8/8: Creating DMG"
    DMG_NAME="Oximy-$VERSION.dmg"

    # Check for create-dmg
    if command -v create-dmg &> /dev/null; then
        echo "Using create-dmg..."
        rm -f "$DMG_NAME" "Oximy $VERSION.dmg" 2>/dev/null || true
        create-dmg "Oximy.app" "." --overwrite 2>&1 || true

        if [ -f "Oximy $VERSION.dmg" ]; then
            mv "Oximy $VERSION.dmg" "$DMG_NAME"
        else
            echo "Falling back to hdiutil..."
            hdiutil create -volname "Oximy" -srcfolder "Oximy.app" -ov -format UDZO "$DMG_NAME"
        fi
    else
        echo "create-dmg not found, using hdiutil..."
        hdiutil create -volname "Oximy" -srcfolder "Oximy.app" -ov -format UDZO "$DMG_NAME"
    fi

    print_success "DMG created: $DMG_NAME"
    ls -lh "$DMG_NAME"

    # Done!
    print_header "macOS Build Complete!"
    echo ""
    echo "Output files in: $SCRIPT_DIR/OximyMac/build/"
    echo ""
    ls -lh "$SCRIPT_DIR/OximyMac/build/"*.dmg 2>/dev/null || true
    echo ""
    echo "To test: open $SCRIPT_DIR/OximyMac/build/Oximy.app"
    echo ""
    echo "To release:"
    echo "  1. Create GitHub release tagged 'oximy-v$VERSION'"
    echo "  2. Upload: Oximy-$VERSION.dmg"
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
    print_header "Step 2/3: Building with Velopack"

    cd scripts
    $POWERSHELL -ExecutionPolicy Bypass -File build.ps1 -Release -Clean -CreateVelopack -Version "$VERSION"

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
