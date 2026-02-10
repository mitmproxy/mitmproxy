# Oximy Windows Pre-Install Script
# Runs before installation to prepare the system.
# Similar to macOS preinstall script.

param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    if (-not $Silent) {
        Write-Host $Message
    }
}

Write-Log "=== Oximy Pre-Install ==="

# Check Windows version (require Windows 10 1903+ / build 18362)
$osVersion = [System.Environment]::OSVersion.Version
if ($osVersion.Build -lt 18362) {
    Write-Error "Oximy requires Windows 10 version 1903 or later (build 18362+)"
    exit 1
}
Write-Log "Windows version check passed (build $($osVersion.Build))"

# Stop existing Oximy instance if running
$oximyProcess = Get-Process -Name "OximyWindows" -ErrorAction SilentlyContinue
if ($oximyProcess) {
    Write-Log "Stopping existing Oximy instance..."
    Stop-Process -Name "OximyWindows" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # Verify it stopped
    $stillRunning = Get-Process -Name "OximyWindows" -ErrorAction SilentlyContinue
    if ($stillRunning) {
        Write-Warning "Oximy process is still running. Installation may fail."
    } else {
        Write-Log "Oximy stopped successfully"
    }
} else {
    Write-Log "No existing Oximy instance found"
}

# Stop mitmdump if running
$mitmProcess = Get-Process -Name "mitmdump" -ErrorAction SilentlyContinue
if ($mitmProcess) {
    Write-Log "Stopping mitmdump process..."
    Stop-Process -Name "mitmdump" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Disable proxy if it was enabled (safety measure)
Write-Log "Ensuring proxy is disabled..."
try {
    $proxyRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $currentProxy = Get-ItemProperty -Path $proxyRegPath -Name "ProxyEnable" -ErrorAction SilentlyContinue
    if ($currentProxy -and $currentProxy.ProxyEnable -eq 1) {
        Set-ItemProperty -Path $proxyRegPath -Name "ProxyEnable" -Value 0
        Write-Log "Proxy disabled"

        # Notify system of proxy change
        $signature = @'
[DllImport("wininet.dll", SetLastError = true, CharSet=CharSet.Auto)]
public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
'@
        try {
            $type = Add-Type -MemberDefinition $signature -Name "WinINet" -Namespace "Win32" -PassThru
            $INTERNET_OPTION_SETTINGS_CHANGED = 39
            $INTERNET_OPTION_REFRESH = 37
            [Win32.WinINet]::InternetSetOption([IntPtr]::Zero, $INTERNET_OPTION_SETTINGS_CHANGED, [IntPtr]::Zero, 0) | Out-Null
            [Win32.WinINet]::InternetSetOption([IntPtr]::Zero, $INTERNET_OPTION_REFRESH, [IntPtr]::Zero, 0) | Out-Null
        } catch {
            Write-Log "Note: Could not notify system of proxy change"
        }
    } else {
        Write-Log "Proxy was not enabled"
    }
} catch {
    Write-Warning "Failed to check/disable proxy: $_"
}

Write-Log "=== Pre-Install Complete ==="
exit 0
