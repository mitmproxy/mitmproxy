#!/bin/bash
# Oximy PKG Build Script
# Creates a signed, notarized PKG installer for MDM deployment
#
# Usage:
#   ./build-pkg.sh                          # Build unsigned PKG
#   DEVELOPER_ID="..." ./build-pkg.sh       # Build signed app + PKG
#   INSTALLER_CERT="..." ./build-pkg.sh     # Also sign the PKG
#
# Required environment variables for signed builds:
#   DEVELOPER_ID  - Developer ID Application certificate (for app signing)
#   INSTALLER_CERT - Developer ID Installer certificate (for PKG signing)
#
# Optional environment variables:
#   VERSION - Version number (default: 1.0.0)
#   APPLE_ID - Apple ID for notarization
#   APPLE_APP_PASSWORD - App-specific password for notarization
#   TEAM_ID - Apple Developer Team ID

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
INSTALLER_DIR="$PROJECT_DIR/Installer"
APP_NAME="Oximy"
VERSION="${VERSION:-1.0.0}"
BUNDLE_ID="com.oximy.mac"

echo "=== Oximy PKG Build for MDM ==="
echo "Version: $VERSION"
echo "Project: $PROJECT_DIR"
echo ""

# Step 1: Build the app bundle using existing script
echo "[1/6] Building app bundle..."
"$SCRIPT_DIR/build-release.sh"

APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
if [ ! -d "$APP_BUNDLE" ]; then
    echo "ERROR: App bundle not found at $APP_BUNDLE"
    exit 1
fi

# Step 2: Create PKG staging directory
echo "[2/6] Creating PKG staging directory..."
PKG_STAGING="$BUILD_DIR/pkg-staging"
PKG_ROOT="$PKG_STAGING/root"
PKG_SCRIPTS="$PKG_STAGING/scripts"

rm -rf "$PKG_STAGING"
mkdir -p "$PKG_ROOT/Applications"
mkdir -p "$PKG_SCRIPTS"

# Copy app to staging
echo "    Copying app bundle to staging..."
cp -R "$APP_BUNDLE" "$PKG_ROOT/Applications/"

# Copy installer scripts
echo "    Copying installer scripts..."
cp "$INSTALLER_DIR/Scripts/preinstall" "$PKG_SCRIPTS/"
cp "$INSTALLER_DIR/Scripts/postinstall" "$PKG_SCRIPTS/"
chmod +x "$PKG_SCRIPTS/"*

# Step 3: Build component package
echo "[3/6] Building component package..."
COMPONENT_PKG="$BUILD_DIR/OximyComponent.pkg"

pkgbuild \
    --root "$PKG_ROOT" \
    --install-location "/" \
    --scripts "$PKG_SCRIPTS" \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    --ownership recommended \
    "$COMPONENT_PKG"

# Step 4: Build distribution package
echo "[4/6] Building distribution package..."
UNSIGNED_PKG="$BUILD_DIR/$APP_NAME-$VERSION-unsigned.pkg"
FINAL_PKG="$BUILD_DIR/$APP_NAME-$VERSION.pkg"

# Create distribution XML
DIST_XML="$BUILD_DIR/distribution.xml"
cat > "$DIST_XML" << EOF
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
EOF

productbuild \
    --distribution "$DIST_XML" \
    --package-path "$BUILD_DIR" \
    --version "$VERSION" \
    "$UNSIGNED_PKG"

# Step 5: Sign the package (if INSTALLER_CERT is set)
echo "[5/6] Signing package..."
if [ -n "$INSTALLER_CERT" ]; then
    echo "    Signing with: $INSTALLER_CERT"
    productsign \
        --sign "$INSTALLER_CERT" \
        "$UNSIGNED_PKG" \
        "$FINAL_PKG"
    rm "$UNSIGNED_PKG"
    echo "    PKG signed successfully"
else
    mv "$UNSIGNED_PKG" "$FINAL_PKG"
    echo "    STUB: Skipping PKG signing (no INSTALLER_CERT set)"
    echo "    To sign PKG, set: INSTALLER_CERT='Developer ID Installer: Your Name (TEAMID)'"
fi

# Step 6: Notarize (if credentials are set)
echo "[6/6] Notarization..."
if [ -n "$APPLE_ID" ] && [ -n "$APPLE_APP_PASSWORD" ] && [ -n "$TEAM_ID" ]; then
    echo "    Submitting for notarization..."
    xcrun notarytool submit "$FINAL_PKG" \
        --apple-id "$APPLE_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --team-id "$TEAM_ID" \
        --wait

    echo "    Stapling notarization ticket..."
    xcrun stapler staple "$FINAL_PKG"
    echo "    Notarization complete"
else
    echo "    STUB: Skipping notarization (credentials not set)"
    echo "    To notarize, set: APPLE_ID, APPLE_APP_PASSWORD, TEAM_ID"
fi

# Cleanup
rm -rf "$PKG_STAGING"
rm -f "$COMPONENT_PKG"
rm -f "$DIST_XML"

# Remove source app bundle to prevent installer relocation issues
# (installer relocates to existing bundle with same ID if found)
rm -rf "$APP_BUNDLE"

echo ""
echo "=== PKG Build Complete ==="
echo ""
echo "PKG Installer: $FINAL_PKG"
echo ""
echo "To install via command line:"
echo "  sudo installer -pkg '$FINAL_PKG' -target /"
echo ""
echo "For MDM deployment:"
echo "  1. Upload PKG to your MDM (Jamf, Kandji, Intune, etc.)"
echo "  2. Create a configuration profile with managed preferences (com.oximy.mac)"
echo "  3. Deploy to target devices"
echo ""
