#!/bin/bash

# Create Xcode Project for OximyMac
# Run this script to generate the .xcodeproj

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Creating Xcode project for OximyMac..."

# Check if xcodegen is installed
if ! command -v xcodegen &> /dev/null; then
    echo "Installing XcodeGen via Homebrew..."
    brew install xcodegen
fi

# Create project.yml for XcodeGen
cat > project.yml << 'EOF'
name: OximyMac
options:
  bundleIdPrefix: com.oximy
  deploymentTarget:
    macOS: "13.0"
  xcodeVersion: "15.0"
  generateEmptyDirectories: true

settings:
  base:
    PRODUCT_NAME: Oximy
    MARKETING_VERSION: "1.0.0"
    CURRENT_PROJECT_VERSION: "1"
    INFOPLIST_FILE: Info.plist
    CODE_SIGN_ENTITLEMENTS: OximyMac.entitlements
    ENABLE_HARDENED_RUNTIME: YES
    SWIFT_VERSION: "5.9"

targets:
  OximyMac:
    type: application
    platform: macOS
    sources:
      - path: App
        group: App
      - path: Views
        group: Views
      - path: Services
        group: Services
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.oximy.mac
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        LD_RUNPATH_SEARCH_PATHS:
          - $(inherited)
          - "@executable_path/../Frameworks"
    info:
      path: Info.plist
      properties:
        LSUIElement: true
        CFBundleDisplayName: Oximy
        NSHumanReadableCopyright: "Copyright 2024 Oximy Inc. All rights reserved."
EOF

# Run XcodeGen
xcodegen generate

echo ""
echo "Done! Open OximyMac.xcodeproj in Xcode."
echo ""
echo "Next steps:"
echo "1. Open OximyMac.xcodeproj"
echo "2. Select your Development Team in Signing & Capabilities"
echo "3. Build and Run (Cmd+R)"
