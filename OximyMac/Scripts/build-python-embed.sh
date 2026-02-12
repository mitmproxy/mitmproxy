#!/bin/bash
# Build FULLY STANDALONE Python environment with mitmproxy for OximyMac
# This creates a completely self-contained, relocatable Python that works on any Mac
# No system Python or mitmproxy installation required!
#
# Note: Builds for BOTH architectures (ARM64 + x86_64) to support Universal Binary.
# At runtime, the app detects architecture and uses the appropriate Python.
#
# IMPORTANT: This script installs mitmproxy from the LOCAL source (not PyPI)
# to include Oximy customizations (CONF_BASENAME = "oximy", etc.)

set -e

# Bypass Oximy proxy for pip — the proxy isn't running during builds
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy no_proxy NO_PROXY

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OXIMY_MAC_DIR="$(dirname "$SCRIPT_DIR")"
RESOURCES_DIR="$OXIMY_MAC_DIR/Resources"
EMBED_DIR="$RESOURCES_DIR/python-embed"
BUILD_DIR="$OXIMY_MAC_DIR/.build-python"

# Path to local mitmproxy source (parent of OximyMac)
MITMPROXY_SOURCE="$(dirname "$OXIMY_MAC_DIR")"

# Python version to bundle (mitmproxy requires >= 3.12)
# Using python-build-standalone releases from https://github.com/indygreg/python-build-standalone/releases
PYTHON_VERSION="3.12.8"
PYTHON_RELEASE_DATE="20241219"

# Build for both architectures to support Universal Binary
BUILD_UNIVERSAL="${BUILD_UNIVERSAL:-true}"

echo "=== Building Standalone Python Embed for OximyMac ==="
echo "Universal Build: $BUILD_UNIVERSAL"
echo "Python Version: $PYTHON_VERSION"
echo "Mitmproxy Source: $MITMPROXY_SOURCE"
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
PYTHON_RELEASE_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_RELEASE_DATE}"

# Function to download Python for a specific architecture (download only, no pip install)
download_python_arch() {
    local arch_name="$1"  # "arm64" or "x86_64"
    local python_tag="$2" # "aarch64-apple-darwin" or "x86_64-apple-darwin"
    local target_dir="$3" # Directory to install to

    local archive="cpython-${PYTHON_VERSION}+${PYTHON_RELEASE_DATE}-${python_tag}-install_only.tar.gz"
    local url="${PYTHON_RELEASE_URL}/${archive}"

    echo ""
    echo "=== Downloading Python for $arch_name ==="
    echo "URL: $url"

    cd "$BUILD_DIR"
    rm -rf "python-$arch_name" "python-$arch_name.tar.gz" "python"

    if ! curl -L -o "python-$arch_name.tar.gz" "$url"; then
        echo "ERROR: Failed to download Python for $arch_name"
        return 1
    fi

    echo "Extracting Python for $arch_name..."
    mkdir -p "python-$arch_name"
    # Extract to current directory first, then move contents
    tar -xzf "python-$arch_name.tar.gz"
    # The archive extracts to a "python" directory
    if [ -d "python" ]; then
        mv python/* "python-$arch_name/"
        rmdir python
    fi

    # Move to target directory
    mkdir -p "$target_dir"
    cp -R "python-$arch_name/"* "$target_dir/"

    echo "✓ Python $arch_name downloaded"
    return 0
}

# Function to install packages for a specific architecture using cross-platform pip
# Uses host pip to download platform-specific wheels, then installs to target
install_packages_for_arch() {
    local arch_name="$1"      # "arm64" or "x86_64"
    local target_dir="$2"     # Target Python directory
    local pip_executable="$3" # Host pip to use for downloading/installing

    echo ""
    echo "=== Installing packages for $arch_name ==="

    local site_packages="$target_dir/lib/python3.12/site-packages"
    local pip_platform=""

    if [ "$arch_name" = "arm64" ]; then
        pip_platform="macosx_11_0_arm64"
    else
        pip_platform="macosx_10_9_x86_64"
    fi

    # Check if we can run the target Python directly (same architecture)
    if "$target_dir/bin/python3" --version >/dev/null 2>&1; then
        echo "    Running native pip for $arch_name..."
        "$target_dir/bin/pip3" install --upgrade pip

        # Pre-install ruamel.yaml WITHOUT the C extension
        echo "    Pre-installing ruamel.yaml (pure Python, no C extension)..."
        "$target_dir/bin/pip3" install "ruamel.yaml>=0.18.10,<=0.19.0" --no-binary ruamel.yaml.clib --no-deps

        # Install mitmproxy from local source
        "$target_dir/bin/pip3" install "$MITMPROXY_SOURCE" jsonata-python psutil watchfiles sentry-sdk
    else
        echo "    Cross-installing packages for $arch_name (cannot run $arch_name Python on this host)..."

        # Strategy: Copy pure Python packages from the already-built architecture,
        # then replace only arch-specific binaries
        # This is more reliable than trying to download and install wheels separately

        # Determine source architecture (the one that's already built)
        local source_arch=""
        if [ "$arch_name" = "arm64" ]; then
            source_arch="x86_64"
        else
            source_arch="arm64"
        fi

        local source_site_packages="$EMBED_DIR/$source_arch/lib/python3.12/site-packages"

        if [ -d "$source_site_packages/mitmproxy" ]; then
            echo "    Copying packages from $source_arch to $arch_name..."
            # Copy all packages (most are pure Python and work on both architectures)
            cp -R "$source_site_packages"/* "$site_packages/"

            # Copy ALL pip-installed scripts from source/bin to target/bin
            # These are Python entry point scripts that work on both architectures
            local source_bin="$EMBED_DIR/$source_arch/bin"
            local target_bin="$target_dir/bin"
            echo "    Copying pip-installed scripts to $arch_name/bin/..."

            # Copy any script that exists in source/bin but not in target/bin
            for script in "$source_bin"/*; do
                script_name=$(basename "$script")
                # Skip if already exists in target (base Python scripts)
                if [ ! -e "$target_bin/$script_name" ]; then
                    if [ -f "$script" ]; then
                        cp "$script" "$target_bin/"
                        # Fix shebang to be portable
                        if head -1 "$target_bin/$script_name" | grep -q "python"; then
                            sed -i '' "1s|.*python.*|#!/usr/bin/env python3|" "$target_bin/$script_name" 2>/dev/null || true
                        fi
                        chmod +x "$target_bin/$script_name"
                        echo "      Copied: $script_name"
                    fi
                fi
            done

            # Now replace architecture-specific compiled extensions
            echo "    Downloading $arch_name-specific compiled extensions..."

            local wheel_dir="$BUILD_DIR/wheels-$arch_name"
            rm -rf "$wheel_dir"
            mkdir -p "$wheel_dir"

            # Determine platform tag for downloads
            local platform_tag=""
            if [ "$arch_name" = "arm64" ]; then
                platform_tag="macosx_11_0_arm64"
            else
                platform_tag="macosx_10_9_x86_64"
            fi

            # Download architecture-specific wheels for packages with compiled extensions
            "$pip_executable" download \
                --platform "$platform_tag" \
                --python-version 3.12 \
                --only-binary=:all: \
                --no-deps \
                -d "$wheel_dir" \
                aioquic==1.2.0 \
                brotli==1.2.0 \
                cryptography==46.0.3 \
                msgpack==1.1.2 \
                tornado==6.5.4 \
                zstandard==0.25.0 \
                cffi==2.0.0 \
                markupsafe==3.0.3 \
                argon2-cffi-bindings==25.1.0 \
                pylsqpack==0.3.23 \
                bcrypt==5.0.0 \
                psutil \
                watchfiles \
                2>/dev/null || true

            # Extract wheels and overwrite the source architecture's compiled files
            echo "    Extracting $arch_name compiled extensions..."
            for whl in "$wheel_dir"/*.whl; do
                if [ -f "$whl" ]; then
                    unzip -q -o "$whl" -d "$site_packages" 2>/dev/null || true
                fi
            done

            rm -rf "$wheel_dir"
        else
            echo "    ERROR: $source_arch packages not found. Build $source_arch first!"
            return 1
        fi
    fi

    # Remove any ruamel.yaml C extension that may cause issues
    echo "    Removing ruamel.yaml C extension (if present)..."
    rm -f "$site_packages/_ruamel_yaml"*.so 2>/dev/null || true
    rm -f "$site_packages/ruamel.yaml.clib"* 2>/dev/null || true

    # Verify critical packages are installed
    if [ ! -f "$site_packages/kaitaistruct.py" ]; then
        echo "    WARNING: kaitaistruct.py not found, downloading directly..."
        "$pip_executable" download --no-deps -d "$BUILD_DIR" kaitaistruct==0.11 2>/dev/null
        unzip -q -o "$BUILD_DIR/kaitaistruct-0.11"*.whl -d "$site_packages" 2>/dev/null || true
        rm -f "$BUILD_DIR/kaitaistruct-0.11"*.whl
    fi

    echo "✓ Python $arch_name packages installed"
    return 0
}

if [ "$BUILD_UNIVERSAL" = "true" ]; then
    # Download BOTH architectures for Universal Binary support
    echo "Building Universal Python embed (arm64 + x86_64)..."

    # Create architecture-specific directories
    mkdir -p "$EMBED_DIR/arm64"
    mkdir -p "$EMBED_DIR/x86_64"

    # Download ARM64 Python
    if ! download_python_arch "arm64" "aarch64-apple-darwin" "$EMBED_DIR/arm64"; then
        echo "ERROR: Failed to download ARM64 Python"
        exit 1
    fi

    # Download x86_64 Python
    if ! download_python_arch "x86_64" "x86_64-apple-darwin" "$EMBED_DIR/x86_64"; then
        echo "ERROR: Failed to download x86_64 Python"
        exit 1
    fi

    # Install packages - do x86_64 first since we'll use its pip for cross-install
    HOST_ARCH=$(uname -m)
    if [ "$HOST_ARCH" = "arm64" ]; then
        # Host is arm64, install arm64 first (native), then cross-install x86_64
        install_packages_for_arch "arm64" "$EMBED_DIR/arm64" "$EMBED_DIR/arm64/bin/pip3"
        install_packages_for_arch "x86_64" "$EMBED_DIR/x86_64" "$EMBED_DIR/arm64/bin/pip3"
    else
        # Host is x86_64, install x86_64 first (native), then cross-install arm64
        install_packages_for_arch "x86_64" "$EMBED_DIR/x86_64" "$EMBED_DIR/x86_64/bin/pip3"
        install_packages_for_arch "arm64" "$EMBED_DIR/arm64" "$EMBED_DIR/x86_64/bin/pip3"
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

    # Install packages for single architecture (native pip works)
    install_packages_for_arch "$ARCH" "$EMBED_DIR" "$EMBED_DIR/bin/pip3"
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
export PYTHONPATH="$PYTHON_HOME/lib/python3.12/site-packages"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1

# Run the pip-installed mitmdump script (works better than -m)
exec "$PYTHON_HOME/bin/python3" "$PYTHON_HOME/bin/mitmdump" "$@"
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
export PYTHONPATH="$PYTHON_HOME/lib/python3.12/site-packages"

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
export PYTHONPATH="$PYTHON_HOME/lib/python3.12/site-packages"
export PATH="$SCRIPT_DIR:$PATH"

# Run the pip-installed mitmdump script (works better than -m)
exec "$SCRIPT_DIR/python3" "$SCRIPT_DIR/mitmdump" "$@"
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
export PYTHONPATH="$PYTHON_HOME/lib/python3.12/site-packages"
# Prevent Python from adding current directory to sys.path
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1

# Run the pip-installed mitmdump script (works better than -m)
exec "$SCRIPT_DIR/python3" "$SCRIPT_DIR/mitmdump" "$@"
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

# Verify both architectures have critical packages (for universal builds)
if [ "$BUILD_UNIVERSAL" = "true" ]; then
    echo ""
    echo "Verifying both architectures have critical dependencies..."
    VERIFICATION_FAILED=false

    for arch_dir in "$EMBED_DIR/arm64" "$EMBED_DIR/x86_64"; do
        arch_name=$(basename "$arch_dir")
        site_packages="$arch_dir/lib/python3.12/site-packages"

        # Check for kaitaistruct (critical TLS parsing dependency)
        if [ ! -f "$site_packages/kaitaistruct.py" ]; then
            echo "ERROR: $arch_name missing kaitaistruct.py!"
            VERIFICATION_FAILED=true
        else
            echo "✓ $arch_name has kaitaistruct.py"
        fi

        # Check for mitmproxy
        if [ ! -d "$site_packages/mitmproxy" ]; then
            echo "ERROR: $arch_name missing mitmproxy package!"
            VERIFICATION_FAILED=true
        else
            echo "✓ $arch_name has mitmproxy"
        fi
    done

    if [ "$VERIFICATION_FAILED" = "true" ]; then
        echo ""
        echo "ERROR: Cross-architecture package installation failed!"
        echo "Some packages may not have arm64 wheels available."
        echo "Consider building on an Apple Silicon Mac instead."
        exit 1
    fi
fi

# Verify installation (runs on host architecture)
echo ""
echo "Verifying installation on host architecture..."
if "$EMBED_DIR/bin/mitmdump" --version; then
    echo ""

    # Verify CONF_BASENAME is set to "oximy"
    echo "Verifying Oximy customizations..."
    CONF_BASENAME=$("$EMBED_DIR/bin/python3" -c "from mitmproxy.options import CONF_BASENAME; print(CONF_BASENAME)" 2>/dev/null)
    if [ "$CONF_BASENAME" = "oximy" ]; then
        echo "✓ CONF_BASENAME = oximy (certificate files will be oximy-ca*.pem)"
    else
        echo "ERROR: CONF_BASENAME = '$CONF_BASENAME' (expected 'oximy')"
        echo "The local mitmproxy source may not have been installed correctly."
        exit 1
    fi

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
