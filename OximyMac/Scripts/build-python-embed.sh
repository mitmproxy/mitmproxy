#!/bin/bash
# Build FULLY STANDALONE Python environment with mitmproxy for OximyMac
# This creates a completely self-contained, relocatable Python that works on any Mac
# No system Python or mitmproxy installation required!
#
# Note: Builds for BOTH architectures (ARM64 + x86_64) to support Universal Binary.
# At runtime, the app detects architecture and uses the appropriate Python.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OXIMY_MAC_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$OXIMY_MAC_DIR/Resources"
EMBED_DIR="$RESOURCES_DIR/python-embed"
BUILD_DIR="$OXIMY_MAC_DIR/.build-python"

# Python version to bundle
PYTHON_VERSION="3.11.9"

# Build for both architectures to support Universal Binary
BUILD_UNIVERSAL="${BUILD_UNIVERSAL:-true}"

echo "=== Building Standalone Python Embed for OximyMac ==="
echo "Universal Build: $BUILD_UNIVERSAL"
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

# Function to download and setup Python for a specific architecture
download_python_arch() {
    local arch_name="$1"  # "arm64" or "x86_64"
    local python_tag="$2" # "aarch64-apple-darwin" or "x86_64-apple-darwin"
    local target_dir="$3" # Directory to install to

    local archive="cpython-${PYTHON_VERSION}+20240415-${python_tag}-install_only.tar.gz"
    local url="${PYTHON_RELEASE_URL}/${archive}"

    echo ""
    echo "=== Downloading Python for $arch_name ==="
    echo "URL: $url"

    cd "$BUILD_DIR"
    rm -rf "python-$arch_name" "python-$arch_name.tar.gz"

    if ! curl -L -o "python-$arch_name.tar.gz" "$url"; then
        echo "ERROR: Failed to download Python for $arch_name"
        return 1
    fi

    echo "Extracting Python for $arch_name..."
    mkdir -p "python-$arch_name"
    tar -xzf "python-$arch_name.tar.gz" -C "python-$arch_name" --strip-components=1 2>/dev/null || \
    tar -xzf "python-$arch_name.tar.gz" && mv python "python-$arch_name/python" && mv "python-$arch_name/python/"* "python-$arch_name/" && rmdir "python-$arch_name/python"

    # Move to target directory
    mkdir -p "$target_dir"
    cp -R "python-$arch_name/"* "$target_dir/"

    echo "Installing mitmproxy for $arch_name..."
    "$target_dir/bin/pip3" install --upgrade pip
    "$target_dir/bin/pip3" install mitmproxy

    echo "✓ Python $arch_name ready"
    return 0
}

if [ "$BUILD_UNIVERSAL" = "true" ]; then
    # Download BOTH architectures for Universal Binary support
    echo "Building Universal Python embed (arm64 + x86_64)..."

    # Create architecture-specific directories
    mkdir -p "$EMBED_DIR/arm64"
    mkdir -p "$EMBED_DIR/x86_64"

    # Download ARM64
    if ! download_python_arch "arm64" "aarch64-apple-darwin" "$EMBED_DIR/arm64"; then
        echo "ERROR: Failed to setup ARM64 Python"
        exit 1
    fi

    # Download x86_64
    if ! download_python_arch "x86_64" "x86_64-apple-darwin" "$EMBED_DIR/x86_64"; then
        echo "ERROR: Failed to setup x86_64 Python"
        exit 1
    fi

    # Create architecture-detecting wrapper scripts in the main bin directory
    mkdir -p "$EMBED_DIR/bin"

else
    # Single architecture build (for local development/testing)
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        PYTHON_BUILD_TAG="aarch64-apple-darwin"
    else
        PYTHON_BUILD_TAG="x86_64-apple-darwin"
    fi

    echo "Building single-architecture Python embed ($ARCH)..."

    if ! download_python_arch "$ARCH" "$PYTHON_BUILD_TAG" "$EMBED_DIR"; then
        echo "ERROR: Failed to setup Python"
        exit 1
    fi
fi

# Create architecture-detecting wrapper scripts
# These detect the current CPU architecture and use the appropriate Python

if [ "$BUILD_UNIVERSAL" = "true" ]; then
    # Universal build: create wrappers that detect architecture
    cat > "$EMBED_DIR/bin/mitmdump" << 'MITMDUMP_EOF'
#!/bin/bash
# Universal mitmdump wrapper - auto-detects architecture
# Supports both Apple Silicon (arm64) and Intel (x86_64) Macs

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EMBED_DIR="$(dirname "$SCRIPT_DIR")"

# Detect CPU architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    PYTHON_HOME="$EMBED_DIR/arm64"
else
    PYTHON_HOME="$EMBED_DIR/x86_64"
fi

# Set up isolated environment for the standalone Python
export PYTHONHOME="$PYTHON_HOME"
export PYTHONPATH="$PYTHON_HOME/lib/python3.11/site-packages"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1

# Run mitmdump with all arguments passed through
exec "$PYTHON_HOME/bin/python3" -I -m mitmproxy.tools.main mitmdump "$@"
MITMDUMP_EOF

    cat > "$EMBED_DIR/bin/python3" << 'PYTHON_EOF'
#!/bin/bash
# Universal Python wrapper - auto-detects architecture

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EMBED_DIR="$(dirname "$SCRIPT_DIR")"

# Detect CPU architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    PYTHON_HOME="$EMBED_DIR/arm64"
else
    PYTHON_HOME="$EMBED_DIR/x86_64"
fi

export PYTHONHOME="$PYTHON_HOME"
export PYTHONPATH="$PYTHON_HOME/lib/python3.11/site-packages"

exec "$PYTHON_HOME/bin/python3" "$@"
PYTHON_EOF

    chmod +x "$EMBED_DIR/bin/mitmdump"
    chmod +x "$EMBED_DIR/bin/python3"

else
    # Single architecture build: create simple wrappers
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
fi

# Clean up build directory
rm -rf "$BUILD_DIR"

# Fix shebangs in pip-created scripts to be relocatable
# pip hardcodes absolute paths which breaks portability
echo ""
echo "Fixing shebangs for relocatability..."

if [ "$BUILD_UNIVERSAL" = "true" ]; then
    # For universal builds, fix shebangs in both architecture directories
    for arch_dir in "$EMBED_DIR/arm64" "$EMBED_DIR/x86_64"; do
        if [ -d "$arch_dir/bin" ]; then
            for script in "$arch_dir/bin/"*; do
                if [ -f "$script" ] && head -1 "$script" | grep -q "^#!.*python"; then
                    if head -1 "$script" | grep -q "^#!/bin/bash"; then
                        continue
                    fi
                    sed -i '' '1s|^#!.*/python.*|#!/usr/bin/env python3|' "$script" 2>/dev/null || true
                fi
            done
            chmod +x "$arch_dir/bin/"* 2>/dev/null || true
        fi
    done
else
    for script in "$EMBED_DIR/bin/"*; do
        if [ -f "$script" ] && head -1 "$script" | grep -q "^#!.*python"; then
            if head -1 "$script" | grep -q "^#!/bin/bash"; then
                continue
            fi
            if grep -q "from mitmproxy" "$script" 2>/dev/null; then
                continue
            fi
            sed -i '' '1s|^#!.*/python.*|#!/usr/bin/env python3|' "$script" 2>/dev/null || true
        fi
    done
fi

# Make all scripts executable
chmod +x "$EMBED_DIR/bin/"* 2>/dev/null || true

# Verify installation
echo ""
echo "Verifying installation..."
if "$EMBED_DIR/bin/mitmdump" --version; then
    echo ""
    echo "=== Build Complete ==="
    echo ""
    echo "mitmdump: $EMBED_DIR/bin/mitmdump"
    echo ""
    echo "Size: $(du -sh "$EMBED_DIR" | cut -f1)"
    echo ""
    if [ "$BUILD_UNIVERSAL" = "true" ]; then
        echo "This is a UNIVERSAL Python bundle (arm64 + x86_64)."
        echo "Supports both Apple Silicon and Intel Macs natively!"
        echo ""
        echo "ARM64 size: $(du -sh "$EMBED_DIR/arm64" | cut -f1)"
        echo "x86_64 size: $(du -sh "$EMBED_DIR/x86_64" | cut -f1)"
    else
        echo "This Python bundle is FULLY STANDALONE and relocatable."
        echo "No system Python or mitmproxy installation required!"
    fi
else
    echo ""
    echo "ERROR: Verification failed. mitmdump could not run."
    exit 1
fi
