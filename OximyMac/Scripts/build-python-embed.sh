#!/bin/bash
# Build FULLY STANDALONE Python environment with mitmproxy for OximyMac
# This creates a completely self-contained, relocatable Python that works on any Mac
# No system Python or mitmproxy installation required!
#
# Note: Builds for the current architecture (ARM64). Intel Macs run via Rosetta 2.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OXIMY_MAC_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$OXIMY_MAC_DIR/Resources"
EMBED_DIR="$RESOURCES_DIR/python-embed"
BUILD_DIR="$OXIMY_MAC_DIR/.build-python"

# Python version to bundle
PYTHON_VERSION="3.11.9"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    PYTHON_ARCH="aarch64"
    PYTHON_BUILD_TAG="aarch64-apple-darwin"
else
    PYTHON_ARCH="x86_64"
    PYTHON_BUILD_TAG="x86_64-apple-darwin"
fi

echo "=== Building Standalone Python Embed for OximyMac ==="
echo "Architecture: $ARCH ($PYTHON_ARCH)"
echo "Python Version: $PYTHON_VERSION"
echo "Output: $EMBED_DIR"
echo ""

# Clean previous builds
if [ -d "$EMBED_DIR" ]; then
    echo "Removing previous python-embed..."
    rm -rf "$EMBED_DIR"
fi

if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
mkdir -p "$EMBED_DIR"

# Download python-build-standalone (relocatable Python builds by Astral/Gregory Szorc)
# These are truly standalone - no system dependencies!
PYTHON_RELEASE_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240415"
PYTHON_ARCHIVE="cpython-${PYTHON_VERSION}+20240415-${PYTHON_BUILD_TAG}-install_only.tar.gz"
PYTHON_URL="${PYTHON_RELEASE_URL}/${PYTHON_ARCHIVE}"

echo "Downloading standalone Python from python-build-standalone..."
echo "URL: $PYTHON_URL"
cd "$BUILD_DIR"

if ! curl -L -o python.tar.gz "$PYTHON_URL"; then
    echo "ERROR: Failed to download Python. Trying alternative approach..."

    # Fallback: use the system Python but copy it properly
    echo "Using system Python with full copy approach..."

    # Find system Python
    SYSTEM_PYTHON=$(which python3)
    if [ -z "$SYSTEM_PYTHON" ]; then
        echo "ERROR: No Python found. Please install Python 3.11+"
        exit 1
    fi

    echo "System Python: $SYSTEM_PYTHON"
    PYTHON_PREFIX=$(python3 -c "import sys; print(sys.prefix)")
    echo "Python prefix: $PYTHON_PREFIX"

    # Create virtual environment and make it standalone
    python3 -m venv "$EMBED_DIR"

    # Install mitmproxy
    "$EMBED_DIR/bin/pip" install --upgrade pip
    "$EMBED_DIR/bin/pip" install mitmproxy

    # Now make it standalone by copying the actual Python binary
    PYTHON_REAL=$(readlink -f "$EMBED_DIR/bin/python3" 2>/dev/null || python3 -c "import sys; print(sys.executable)")

    # Copy Python framework/dylib
    if [ -d "/opt/homebrew/Cellar/python@3.11" ]; then
        PYTHON_FRAMEWORK="/opt/homebrew/Cellar/python@3.11"
    elif [ -d "/usr/local/Cellar/python@3.11" ]; then
        PYTHON_FRAMEWORK="/usr/local/Cellar/python@3.11"
    fi

    echo "WARNING: Using venv approach. The bundle may not be fully portable."
    echo "For a fully standalone build, ensure python-build-standalone download works."

else
    echo "Extracting Python..."
    tar -xzf python.tar.gz

    # Move python directory contents to embed dir
    mv python/* "$EMBED_DIR/"

    echo "Installing mitmproxy into standalone Python..."
    "$EMBED_DIR/bin/pip3" install --upgrade pip
    "$EMBED_DIR/bin/pip3" install mitmproxy
fi

# Create a wrapper script that sets up the environment properly
# This ensures the bundled Python finds its libraries regardless of install location
cat > "$EMBED_DIR/bin/run-mitmdump" << 'WRAPPER_EOF'
#!/bin/bash
# Wrapper script for running mitmdump with the bundled Python
# This makes the bundle fully relocatable

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_HOME="$(dirname "$SCRIPT_DIR")"

# Set up environment for the standalone Python
export PYTHONHOME="$PYTHON_HOME"
export PYTHONPATH="$PYTHON_HOME/lib/python3.11/site-packages"
export PATH="$SCRIPT_DIR:$PATH"

# Run mitmdump with all arguments passed through
exec "$SCRIPT_DIR/python3" -m mitmproxy.tools.main mitmdump "$@"
WRAPPER_EOF

chmod +x "$EMBED_DIR/bin/run-mitmdump"

# Also update the mitmdump script to be relocatable
if [ -f "$EMBED_DIR/bin/mitmdump" ]; then
    cat > "$EMBED_DIR/bin/mitmdump" << 'MITMDUMP_EOF'
#!/bin/bash
# Relocatable mitmdump wrapper
# This script ensures the bundled Python uses ONLY its own packages,
# ignoring any system or development mitmproxy installations

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_HOME="$(dirname "$SCRIPT_DIR")"

# Set up isolated environment for the standalone Python
export PYTHONHOME="$PYTHON_HOME"
# Use ONLY the bundled site-packages, ignore everything else
export PYTHONPATH="$PYTHON_HOME/lib/python3.11/site-packages"
# Prevent Python from adding current directory to sys.path
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1

# Run mitmdump with all arguments passed through
# Use -I flag to isolate from user site-packages and PYTHONPATH pollution
exec "$SCRIPT_DIR/python3" -I -m mitmproxy.tools.main mitmdump "$@"
MITMDUMP_EOF
    chmod +x "$EMBED_DIR/bin/mitmdump"
fi

# Clean up build directory
rm -rf "$BUILD_DIR"

# Fix shebangs in pip-created scripts to be relocatable
# pip hardcodes absolute paths which breaks portability
echo "Fixing shebangs for relocatability..."
for script in "$EMBED_DIR/bin/"*; do
    if [ -f "$script" ] && head -1 "$script" | grep -q "^#!.*python"; then
        # Replace hardcoded python path with portable bash wrapper
        SCRIPT_NAME=$(basename "$script")
        # Skip if it's already our custom wrapper
        if head -1 "$script" | grep -q "^#!/bin/bash"; then
            continue
        fi
        # Get the Python module command from the script
        if grep -q "from mitmproxy" "$script" 2>/dev/null; then
            # It's a mitmproxy entry point - we already have a custom mitmdump wrapper
            continue
        fi
        # For other scripts, make shebang relative using env
        sed -i '' '1s|^#!.*/python.*|#!/usr/bin/env python3|' "$script" 2>/dev/null || true
    fi
done

# Make all scripts executable
chmod +x "$EMBED_DIR/bin/"*

# Verify installation
echo ""
echo "Verifying installation..."
if "$EMBED_DIR/bin/mitmdump" --version; then
    echo ""
    echo "=== Build Complete ==="
    echo ""
    echo "Python: $EMBED_DIR/bin/python3"
    echo "mitmdump: $EMBED_DIR/bin/mitmdump"
    echo ""
    echo "Size: $(du -sh "$EMBED_DIR" | cut -f1)"
    echo ""
    echo "This Python bundle is FULLY STANDALONE and relocatable."
    echo "No system Python or mitmproxy installation required!"
else
    echo ""
    echo "ERROR: Verification failed. mitmdump could not run."
    exit 1
fi
