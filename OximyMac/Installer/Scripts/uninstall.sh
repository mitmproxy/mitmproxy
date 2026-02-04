#!/bin/bash
# Oximy Uninstall Script
# For MDM-triggered or manual uninstallation
#
# Usage:
#   sudo ./uninstall.sh              # Full uninstall (preserves user data)
#   sudo ./uninstall.sh --purge      # Complete removal including user data
#
# This script can be deployed via MDM for remote uninstallation.

set -e

PURGE_USER_DATA=false
if [ "$1" = "--purge" ]; then
    PURGE_USER_DATA=true
fi

echo "=== Oximy Uninstall ==="
echo ""

# Determine the console user (for user-specific cleanup)
CONSOLE_USER=$(stat -f "%Su" /dev/console 2>/dev/null || echo "")
if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
    USER_HOME=$(eval echo ~"$CONSOLE_USER")
else
    USER_HOME="$HOME"
fi

echo "Console user: ${CONSOLE_USER:-unknown}"
echo "User home: $USER_HOME"
echo ""

# Step 1: Stop Oximy if running
echo "[1/6] Stopping Oximy..."
if pgrep -x "Oximy" > /dev/null || pgrep -x "OximyMac" > /dev/null; then
    pkill -x "Oximy" 2>/dev/null || true
    pkill -x "OximyMac" 2>/dev/null || true
    sleep 2
    echo "    Oximy stopped"
else
    echo "    Oximy not running"
fi

# Also kill any mitmproxy/mitmdump processes
if pgrep -f "mitmdump" > /dev/null; then
    pkill -f "mitmdump" 2>/dev/null || true
    echo "    Stopped mitmproxy processes"
fi

# Step 2: Disable system proxy on all network interfaces
echo "[2/6] Disabling system proxy..."
for service in "Wi-Fi" "Ethernet" "USB 10/100/1000 LAN" "Thunderbolt Ethernet" "Thunderbolt Bridge"; do
    networksetup -setwebproxystate "$service" off 2>/dev/null || true
    networksetup -setsecurewebproxystate "$service" off 2>/dev/null || true
done
echo "    System proxy disabled"

# Step 3: Unload and remove LaunchAgents
echo "[3/6] Removing LaunchAgents..."

# User LaunchAgent
USER_LAUNCH_AGENT="$USER_HOME/Library/LaunchAgents/com.oximy.agent.plist"
if [ -f "$USER_LAUNCH_AGENT" ]; then
    if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
        sudo -u "$CONSOLE_USER" launchctl unload "$USER_LAUNCH_AGENT" 2>/dev/null || true
    fi
    rm -f "$USER_LAUNCH_AGENT"
    echo "    Removed user LaunchAgent"
fi

# System LaunchAgent (MDM-installed)
SYSTEM_LAUNCH_AGENT="/Library/LaunchAgents/com.oximy.agent.plist"
if [ -f "$SYSTEM_LAUNCH_AGENT" ]; then
    launchctl unload "$SYSTEM_LAUNCH_AGENT" 2>/dev/null || true
    rm -f "$SYSTEM_LAUNCH_AGENT"
    echo "    Removed system LaunchAgent"
fi

# Step 4: Remove app bundle
echo "[4/6] Removing application..."
if [ -d "/Applications/Oximy.app" ]; then
    rm -rf "/Applications/Oximy.app"
    echo "    Removed /Applications/Oximy.app"
else
    echo "    Application not found (already removed?)"
fi

# Step 5: Clear UserDefaults/preferences
echo "[5/6] Removing preferences..."
if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
    sudo -u "$CONSOLE_USER" defaults delete com.oximy.mac 2>/dev/null || true
else
    defaults delete com.oximy.mac 2>/dev/null || true
fi
echo "    Preferences removed"

# Step 6: Handle user data
echo "[6/6] Handling user data..."
OXIMY_DIR="$USER_HOME/.oximy"
MITMPROXY_DIR="$USER_HOME/.mitmproxy"

if [ "$PURGE_USER_DATA" = true ]; then
    echo "    Purging user data (--purge specified)..."

    if [ -d "$OXIMY_DIR" ]; then
        rm -rf "$OXIMY_DIR"
        echo "    Removed $OXIMY_DIR"
    fi

    # Remove CA certificate files (but leave other mitmproxy data if any)
    if [ -d "$MITMPROXY_DIR" ]; then
        rm -f "$MITMPROXY_DIR/oximy-ca.pem" 2>/dev/null || true
        rm -f "$MITMPROXY_DIR/oximy-ca-cert.pem" 2>/dev/null || true
        rm -f "$MITMPROXY_DIR/oximy-ca.p12" 2>/dev/null || true
        rm -f "$MITMPROXY_DIR/oximy-dhparam.pem" 2>/dev/null || true
        echo "    Removed Oximy CA files from $MITMPROXY_DIR"

        # Remove directory if empty
        if [ -z "$(ls -A "$MITMPROXY_DIR" 2>/dev/null)" ]; then
            rmdir "$MITMPROXY_DIR" 2>/dev/null || true
        fi
    fi

    # Remove CA certificate from Keychain
    echo "    Removing CA certificate from Keychain..."
    security delete-certificate -c "Oximy CA" 2>/dev/null || true
    security delete-certificate -c "Oximy CA" -t /Library/Keychains/System.keychain 2>/dev/null || true
else
    echo "    Preserving user data at: $OXIMY_DIR"
    echo "    To remove completely, run with --purge flag"
fi

echo ""
echo "=== Uninstall Complete ==="
echo ""

if [ "$PURGE_USER_DATA" = true ]; then
    echo "Oximy has been completely removed from this system."
else
    echo "Oximy has been uninstalled."
    echo ""
    echo "User data preserved at:"
    echo "  - $OXIMY_DIR (traces, logs, config)"
    echo "  - $MITMPROXY_DIR (CA certificate)"
    echo ""
    echo "To completely remove all data:"
    echo "  sudo $0 --purge"
fi
echo ""

exit 0
