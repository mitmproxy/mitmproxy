#!/bin/bash
# Build standalone Python environment with mitmproxy for OximyMac
# This creates a self-contained Python that can be bundled in the app

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OXIMY_MAC_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$OXIMY_MAC_DIR/Resources"
EMBED_DIR="$RESOURCES_DIR/python-embed"

echo "=== Building Python Embed for OximyMac ==="
echo "Output: $EMBED_DIR"

# Clean previous build
if [ -d "$EMBED_DIR" ]; then
    echo "Removing previous python-embed..."
    rm -rf "$EMBED_DIR"
fi

mkdir -p "$EMBED_DIR"

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv "$EMBED_DIR"

# Activate and install mitmproxy
echo "Installing mitmproxy..."
source "$EMBED_DIR/bin/activate"
pip install --upgrade pip
pip install mitmproxy

# Verify installation
echo "Verifying installation..."
"$EMBED_DIR/bin/mitmdump" --version

# Copy the Oximy addon
echo "Copying Oximy addon..."
ADDON_SRC="$OXIMY_MAC_DIR/../mitmproxy/addons/oximy"
ADDON_DST="$RESOURCES_DIR/oximy-addon"

if [ -d "$ADDON_SRC" ]; then
    rm -rf "$ADDON_DST"
    cp -r "$ADDON_SRC" "$ADDON_DST"
    echo "Addon copied from: $ADDON_SRC"
else
    echo "WARNING: Addon not found at $ADDON_SRC"
    # Try alternative location
    ALT_ADDON_SRC="$OXIMY_MAC_DIR/../addons/oximy"
    if [ -d "$ALT_ADDON_SRC" ]; then
        rm -rf "$ADDON_DST"
        cp -r "$ALT_ADDON_SRC" "$ADDON_DST"
        echo "Addon copied from: $ALT_ADDON_SRC"
    fi
fi

# Make scripts executable
chmod +x "$EMBED_DIR/bin/"*

echo ""
echo "=== Build Complete ==="
echo "Python: $EMBED_DIR/bin/python3"
echo "mitmdump: $EMBED_DIR/bin/mitmdump"
echo ""
echo "Size: $(du -sh "$EMBED_DIR" | cut -f1)"
echo ""
echo "To test:"
echo "  $EMBED_DIR/bin/mitmdump --version"
