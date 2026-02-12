# OximyMac Build System
#
# Usage:
#   make build      - Sync addon + build (default)
#   make sync       - Just sync the addon files
#   make run        - Sync + build + run
#   make clean      - Clean build artifacts
#   make release    - Build release version
#   make dmg        - Build release DMG for distribution
#   make pkg        - Build PKG installer for MDM deployment

.PHONY: all build sync run clean release pkg help

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
	@echo "==> Building release app bundle..."
	./Scripts/build-release.sh
	@echo "==> Creating DMG with volume icon..."
	@cd build && \
	DMG_TEMP="Oximy-temp.dmg" && \
	DMG_NAME="Oximy.dmg" && \
	APP_ICNS="Oximy.app/Contents/Resources/AppIcon.icns" && \
	rm -f "$$DMG_NAME" "$$DMG_TEMP" 2>/dev/null; \
	hdiutil create -size 300m -fs HFS+ -volname "Oximy" -ov "$$DMG_TEMP" && \
	MOUNT_DIR=$$(hdiutil attach "$$DMG_TEMP" -readwrite -noverify | grep "/Volumes/Oximy" | sed 's/.*\(\/Volumes\/Oximy\)/\1/') && \
	cp -R Oximy.app "$$MOUNT_DIR/" && \
	ln -s /Applications "$$MOUNT_DIR/Applications" && \
	if [ -f "$$APP_ICNS" ]; then \
		cp "$$APP_ICNS" "$$MOUNT_DIR/.VolumeIcon.icns" && \
		SetFile -a C "$$MOUNT_DIR" 2>/dev/null || true; \
	fi && \
	sync && sleep 1 && \
	hdiutil detach "$$MOUNT_DIR" -quiet 2>/dev/null || hdiutil detach "$$MOUNT_DIR" -force 2>/dev/null || true; \
	hdiutil convert "$$DMG_TEMP" -format UDZO -o "$$DMG_NAME" && \
	rm -f "$$DMG_TEMP" && \
	echo "==> DMG ready: build/$$DMG_NAME" && \
	ls -lh "$$DMG_NAME"

# Build PKG installer for MDM deployment
pkg: sync
	@echo "==> Building PKG installer for MDM..."
	./Scripts/build-pkg.sh

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
	@echo "  make pkg       - Build PKG installer for MDM deployment"
	@echo ""
	@echo "The 'sync' step automatically copies Python files from"
	@echo "mitmproxy/addons/oximy/ to Resources/oximy-addon/"
	@echo "and converts absolute imports to relative imports."
	@echo ""
	@echo "For MDM deployment, use 'make pkg' which creates a signed"
	@echo "PKG installer suitable for Jamf, Kandji, Intune, etc."
