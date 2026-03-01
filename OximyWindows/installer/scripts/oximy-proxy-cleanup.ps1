# oximy-proxy-cleanup.ps1
# Runs at every user logon via scheduled task to detect and disable orphaned proxy settings.
# If the previous session ended abruptly (power loss, BSOD), the proxy registry key may
# still point to a dead localhost port, blackholing all HTTP traffic.
# This script mirrors ProxyService.CleanupOrphanedProxy() in the C# app.

$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

# Read current proxy state
$proxyEnable = (Get-ItemProperty -Path $regPath -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable
if ($proxyEnable -ne 1) { exit 0 }

$proxyServer = (Get-ItemProperty -Path $regPath -Name "ProxyServer" -ErrorAction SilentlyContinue).ProxyServer
if (-not $proxyServer -or -not $proxyServer.StartsWith("127.0.0.1:")) { exit 0 }

# Extract port number
$port = 0
$parts = $proxyServer.Split(":")
if ($parts.Length -lt 2 -or -not [int]::TryParse($parts[1], [ref]$port) -or $port -le 0) { exit 0 }

# TCP-connect with 500ms timeout (mirrors ProxyService.IsPortListening)
$alive = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ar = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
    $alive = $ar.AsyncWaitHandle.WaitOne(500) -and $tcp.Connected
    $tcp.Close()
} catch {
    $alive = $false
}

if ($alive) { exit 0 }

# Port is dead — disable proxy and notify browsers
Set-ItemProperty -Path $regPath -Name "ProxyEnable" -Value 0 -ErrorAction SilentlyContinue

$sig = @'
[DllImport("wininet.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
'@
try {
    $t = Add-Type -MemberDefinition $sig -Name "WinINet" -Namespace "ProxyCleanup" -PassThru -ErrorAction SilentlyContinue
    [ProxyCleanup.WinINet]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null  # SETTINGS_CHANGED
    [ProxyCleanup.WinINet]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null  # REFRESH
} catch {}

exit 0
