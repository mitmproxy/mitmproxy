#!/bin/bash
# Sync the oximy addon from mitmproxy source to OximyMac bundle
# This script converts absolute imports to relative imports for standalone use

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OXIMY_MAC_DIR="$(dirname "$SCRIPT_DIR")"
MITMPROXY_DIR="$(dirname "$OXIMY_MAC_DIR")"

SOURCE_DIR="$MITMPROXY_DIR/mitmproxy/addons/oximy"
DEST_DIR="$OXIMY_MAC_DIR/Resources/oximy-addon"

echo "Syncing oximy addon..."
echo "  Source: $SOURCE_DIR"
echo "  Dest:   $DEST_DIR"

# Check source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Create dest if needed
mkdir -p "$DEST_DIR"

# List of Python files to sync
FILES=(
    "addon.py"
    "normalize.py"
    "config.json"
    "process.py"
    "collector.py"
    "oximy_logger.py"
    "sentry_service.py"
    "enforcement.py"
    "playbooks.py"
    "__init__.py"
)

# Sync each file, converting imports
for file in "${FILES[@]}"; do
    src="$SOURCE_DIR/$file"
    dst="$DEST_DIR/$file"

    if [ -f "$src" ]; then
        echo "  Syncing: $file"
        # Convert absolute imports to relative imports
        # from mitmproxy.addons.oximy.module import X -> from module import X
        sed -e 's/from mitmproxy\.addons\.oximy\.\([a-z_]*\)/from \1/g' \
            -e 's/from mitmproxy\.addons\.oximy import/import/g' \
            "$src" > "$dst"
    else
        echo "  Skipping (not found): $file"
    fi
done

# Copy documentation files as-is
for doc in "README.md" "ARCHITECTURE.md"; do
    if [ -f "$SOURCE_DIR/$doc" ]; then
        cp "$SOURCE_DIR/$doc" "$DEST_DIR/"
        echo "  Copied: $doc"
    fi
done

# Clean up __pycache__
rm -rf "$DEST_DIR/__pycache__"

echo "Sync complete!"
echo ""
echo "Files synced to: $DEST_DIR"
ls -la "$DEST_DIR"
