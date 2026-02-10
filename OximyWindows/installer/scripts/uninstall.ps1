# Oximy Windows Uninstall Script
# Performs cleanup on uninstallation.
# Similar to macOS uninstall script.

param(
    [switch]$Purge,     # Remove user data too (traces, logs, etc.)
    [switch]$Silent
)

$ErrorActionPreference = "Continue"

function Write-Log {
    param([string]$Message)
    if (-not $Silent) {
        Write-Host $Message
    }
}

Write-Log "=== Oximy Uninstall ==="

# Define paths
$userProfile = $env:USERPROFILE
$oximyDir = Join-Path $userProfile ".oximy"
$mitmproxyDir = Join-Path $userProfile ".mitmproxy"

# 1. Stop Oximy if running
$oximyProcess = Get-Process -Name "OximyWindows" -ErrorAction SilentlyContinue
if ($oximyProcess) {
    Write-Log "Stopping Oximy..."
    Stop-Process -Name "OximyWindows" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 2. Stop mitmdump processes
$mitmProcess = Get-Process -Name "mitmdump" -ErrorAction SilentlyContinue
if ($mitmProcess) {
    Write-Log "Stopping mitmdump..."
    Stop-Process -Name "mitmdump" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# 3. Disable system proxy
Write-Log "Disabling system proxy..."
try {
    $proxyRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    Set-ItemProperty -Path $proxyRegPath -Name "ProxyEnable" -Value 0 -ErrorAction SilentlyContinue

    # Notify system of proxy change
    $signature = @'
[DllImport("wininet.dll", SetLastError = true, CharSet=CharSet.Auto)]
public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
'@
    try {
        $type = Add-Type -MemberDefinition $signature -Name "WinINet" -Namespace "Win32" -PassThru -ErrorAction SilentlyContinue
        $INTERNET_OPTION_SETTINGS_CHANGED = 39
        $INTERNET_OPTION_REFRESH = 37
        [Win32.WinINet]::InternetSetOption([IntPtr]::Zero, $INTERNET_OPTION_SETTINGS_CHANGED, [IntPtr]::Zero, 0) | Out-Null
        [Win32.WinINet]::InternetSetOption([IntPtr]::Zero, $INTERNET_OPTION_REFRESH, [IntPtr]::Zero, 0) | Out-Null
    } catch {
        # Ignore - best effort
    }
    Write-Log "Proxy disabled"
} catch {
    Write-Warning "Failed to disable proxy: $_"
}

# 4. Remove Scheduled Task (MDM auto-start)
Write-Log "Removing Scheduled Task..."
try {
    schtasks.exe /Delete /TN "Oximy\OximyAutoStart" /F 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Scheduled Task removed"
    }
} catch {
    # Task might not exist - that's OK
}

# 5. Remove HKCU Run key
Write-Log "Removing startup registry entry..."
try {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Oximy" -ErrorAction SilentlyContinue
} catch {
    # Key might not exist - that's OK
}

# 6. Remove URL scheme registration
Write-Log "Removing URL scheme registration..."
try {
    Remove-Item -Path "HKCU:\Software\Classes\oximy" -Recurse -ErrorAction SilentlyContinue
} catch {
    # Key might not exist - that's OK
}

# 7. Handle user data based on Purge flag
if ($Purge) {
    Write-Log "Purging user data..."

    # Remove oximy directory
    if (Test-Path $oximyDir) {
        try {
            Remove-Item $oximyDir -Recurse -Force
            Write-Log "Removed: $oximyDir"
        } catch {
            Write-Warning "Failed to remove $oximyDir : $_"
        }
    }

    # Remove CA certificate files (but not the whole .mitmproxy directory)
    if (Test-Path $mitmproxyDir) {
        try {
            Get-ChildItem -Path $mitmproxyDir -Filter "oximy-ca*" | Remove-Item -Force
            Write-Log "Removed Oximy CA certificate files"
        } catch {
            Write-Warning "Failed to remove CA files: $_"
        }
    }

    # Remove CA from certificate stores
    Write-Log "Removing CA certificate from stores..."
    try {
        # Try to remove from user store
        certutil.exe -delstore -user Root "mitmproxy" 2>$null
        certutil.exe -delstore -user Root "Oximy CA" 2>$null

        # Try to remove from machine store (requires admin)
        certutil.exe -delstore Root "mitmproxy" 2>$null
        certutil.exe -delstore Root "Oximy CA" 2>$null

        Write-Log "CA certificate removal attempted"
    } catch {
        # Best effort - might not have admin rights
    }
} else {
    Write-Log "Preserving user data at: $oximyDir"
    Write-Log "  Use -Purge flag to remove all user data"
}

Write-Log "=== Uninstall Complete ==="
exit 0
