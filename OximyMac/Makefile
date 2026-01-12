# OximyMac Build System
#
# Usage:
#   make build      - Sync addon + build (default)
#   make sync       - Just sync the addon files
#   make run        - Sync + build + run
#   make clean      - Clean build artifacts
#   make release    - Build release version

.PHONY: all build sync run clean release help

# Default target
all: build

# Sync addon files from mitmproxy source (converts imports automatically)
sync:
	@echo "==> Syncing oximy addon from mitmproxy source..."
	@./Scripts/sync-addon.sh

# Build (sync first, then swift build)
build: sync
	@echo "==> Building OximyMac..."
	swift build

# Build and run
run: build
	@echo "==> Running OximyMac..."
	.build/debug/OximyMac

# Clean build artifacts
clean:
	@echo "==> Cleaning..."
	swift package clean
	rm -rf .build

# Release build
release: sync
	@echo "==> Building release..."
	swift build -c release

# Build app bundle (for testing features like auto-update that require .app structure)
bundle: sync
	@echo "==> Building debug app bundle..."
	BUILD_CONFIG=debug ./Scripts/build-release.sh

# Build release app bundle with DMG
dmg: sync
	@echo "==> Building release DMG..."
	./Scripts/build-release.sh

# Help
help:
	@echo "OximyMac Build System"
	@echo ""
	@echo "Usage:"
	@echo "  make build     - Sync addon + build (default)"
	@echo "  make sync      - Just sync the addon files"
	@echo "  make run       - Sync + build + run"
	@echo "  make clean     - Clean build artifacts"
	@echo "  make release   - Build release version"
	@echo "  make bundle    - Build debug app bundle (for testing auto-update)"
	@echo "  make dmg       - Build release DMG for distribution"
	@echo ""
	@echo "The 'sync' step automatically copies Python files from"
	@echo "mitmproxy/addons/oximy/ to Resources/oximy-addon/"
	@echo "and converts absolute imports to relative imports."
