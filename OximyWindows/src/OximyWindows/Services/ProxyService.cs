using System.ComponentModel;
using System.Net;
using System.Net.Sockets;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace OximyWindows.Services;

/// <summary>
/// Manages Windows system proxy settings via the Registry.
/// Configures HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings.
/// </summary>
public class ProxyService : INotifyPropertyChanged
{
    private const string InternetSettingsKey = @"Software\Microsoft\Windows\CurrentVersion\Internet Settings";

    // Store original values for restoration
    private int? _originalProxyEnable;
    private string? _originalProxyServer;
    private string? _originalProxyOverride;

    private bool _isProxyEnabled;
    public bool IsProxyEnabled
    {
        get => _isProxyEnabled;
        private set => SetProperty(ref _isProxyEnabled, value);
    }

    private int? _configuredPort;
    public int? ConfiguredPort
    {
        get => _configuredPort;
        private set => SetProperty(ref _configuredPort, value);
    }

    // MARK: - Startup Cleanup

    /// <summary>
    /// Clean up orphaned proxy settings on app launch.
    /// FAIL-OPEN: If the app crashed with proxy enabled, the system proxy points to a dead port,
    /// blocking all traffic. This detects that case and disables the proxy immediately.
    /// </summary>
    public void CleanupOrphanedProxy()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey);
            if (key == null) return;

            var proxyEnable = key.GetValue("ProxyEnable");
            var proxyServer = key.GetValue("ProxyServer") as string;

            var isEnabled = proxyEnable is int enable && enable == 1;
            if (!isEnabled || string.IsNullOrEmpty(proxyServer) || !proxyServer.StartsWith("127.0.0.1:"))
                return;

            // Proxy is enabled and pointing to localhost — check if the port is alive
            var parts = proxyServer.Split(':');
            if (parts.Length != 2 || !int.TryParse(parts[1], out var port))
                return;

            if (!IsPortListening(port))
            {
                // FAIL-OPEN: Proxy is pointing to a dead port — clear it immediately
                System.Diagnostics.Debug.WriteLine($"[ProxyService] FAIL-OPEN: Found orphaned proxy pointing to dead port {port} - cleaning up");
                DisableProxy();
            }
            else
            {
                System.Diagnostics.Debug.WriteLine($"[ProxyService] Proxy on port {port} is active (something is listening)");
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[ProxyService] Error during orphaned proxy cleanup: {ex.Message}");
        }
    }

    /// <summary>
    /// Check if something is listening on a port (synchronous).
    /// </summary>
    private static bool IsPortListening(int port)
    {
        try
        {
            using var client = new TcpClient();
            var result = client.BeginConnect(IPAddress.Loopback, port, null, null);
            var connected = result.AsyncWaitHandle.WaitOne(TimeSpan.FromMilliseconds(500));
            if (connected && client.Connected)
            {
                client.EndConnect(result);
                return true;
            }
            return false;
        }
        catch (SocketException)
        {
            return false;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// Check current proxy status.
    /// </summary>
    public void CheckStatus()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey);
            if (key != null)
            {
                var proxyEnable = key.GetValue("ProxyEnable");
                var proxyServer = key.GetValue("ProxyServer") as string;

                var isEnabled = proxyEnable is int enable && enable == 1;
                var isOurProxy = proxyServer?.StartsWith("127.0.0.1:") == true;

                IsProxyEnabled = isEnabled && isOurProxy;

                if (IsProxyEnabled && proxyServer != null)
                {
                    var parts = proxyServer.Split(':');
                    if (parts.Length == 2 && int.TryParse(parts[1], out var port))
                    {
                        ConfiguredPort = port;
                    }
                }
                else
                {
                    ConfiguredPort = null;
                }
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to check proxy status: {ex.Message}");
            IsProxyEnabled = false;
            ConfiguredPort = null;
        }
    }

    /// <summary>
    /// Enable the system proxy to route through our local mitmproxy.
    /// </summary>
    public void EnableProxy(int port)
    {
        System.Diagnostics.Debug.WriteLine($"[ProxyService] EnableProxy called with port {port}");
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey, writable: true);
            if (key == null)
                throw new ProxyException("Cannot access Internet Settings registry key");

            // Store original values for rollback
            _originalProxyEnable = key.GetValue("ProxyEnable") as int?;
            _originalProxyServer = key.GetValue("ProxyServer") as string;
            _originalProxyOverride = key.GetValue("ProxyOverride") as string;

            System.Diagnostics.Debug.WriteLine($"[ProxyService] Original values - Enable: {_originalProxyEnable}, Server: {_originalProxyServer}");

            // Set new proxy values
            key.SetValue("ProxyEnable", 1, RegistryValueKind.DWord);
            key.SetValue("ProxyServer", $"127.0.0.1:{port}", RegistryValueKind.String);
            key.SetValue("ProxyOverride", Constants.ProxyBypassList, RegistryValueKind.String);

            System.Diagnostics.Debug.WriteLine($"[ProxyService] Set proxy to 127.0.0.1:{port}");

            // Notify Windows and applications of the change
            NotifySettingsChange();

            IsProxyEnabled = true;
            ConfiguredPort = port;
            System.Diagnostics.Debug.WriteLine("[ProxyService] Proxy enabled successfully");
        }
        catch (Exception ex) when (ex is not ProxyException)
        {
            System.Diagnostics.Debug.WriteLine($"[ProxyService] ERROR enabling proxy: {ex.Message}");
            throw new ProxyException($"Failed to enable proxy: {ex.Message}", ex);
        }
    }

    /// <summary>
    /// Disable the system proxy.
    /// </summary>
    public void DisableProxy()
    {
        System.Diagnostics.Debug.WriteLine("[ProxyService] DisableProxy called");
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey, writable: true);
            if (key == null)
            {
                System.Diagnostics.Debug.WriteLine("[ProxyService] WARNING: Could not open registry key");
                return;
            }

            // Always disable the proxy - don't rely on original values
            key.SetValue("ProxyEnable", 0, RegistryValueKind.DWord);
            System.Diagnostics.Debug.WriteLine("[ProxyService] Set ProxyEnable to 0");

            NotifySettingsChange();

            IsProxyEnabled = false;
            ConfiguredPort = null;
            System.Diagnostics.Debug.WriteLine("[ProxyService] Proxy disabled successfully");
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[ProxyService] ERROR disabling proxy: {ex.Message}");
            // Don't throw - we want cleanup to succeed even if there are errors
        }
    }

    /// <summary>
    /// Update the proxy port (e.g., if mitmproxy restarts on a different port).
    /// </summary>
    public void UpdatePort(int newPort)
    {
        if (!IsProxyEnabled)
            return;

        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey, writable: true);
            if (key == null)
                return;

            key.SetValue("ProxyServer", $"127.0.0.1:{newPort}", RegistryValueKind.String);
            NotifySettingsChange();

            ConfiguredPort = newPort;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to update proxy port: {ex.Message}");
        }
    }

    /// <summary>
    /// Notify Windows and applications of proxy settings change.
    /// This is CRITICAL - without it, browsers won't pick up the change.
    /// </summary>
    private static void NotifySettingsChange()
    {
        // Method 1: InternetSetOption (for IE/Edge/system)
        InternetSetOption(IntPtr.Zero, INTERNET_OPTION_SETTINGS_CHANGED, IntPtr.Zero, 0);
        InternetSetOption(IntPtr.Zero, INTERNET_OPTION_REFRESH, IntPtr.Zero, 0);

        // Method 2: WM_SETTINGCHANGE broadcast (for other apps)
        SendMessageTimeout(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            IntPtr.Zero,
            "Internet Settings",
            SMTO_ABORTIFHUNG,
            1000,
            out _);
    }

    #region P/Invoke Declarations

    private const int INTERNET_OPTION_SETTINGS_CHANGED = 39;
    private const int INTERNET_OPTION_REFRESH = 37;
    private const int WM_SETTINGCHANGE = 0x001A;
    private static readonly IntPtr HWND_BROADCAST = new(0xFFFF);
    private const int SMTO_ABORTIFHUNG = 0x0002;

    [DllImport("wininet.dll", SetLastError = true)]
    private static extern bool InternetSetOption(
        IntPtr hInternet,
        int dwOption,
        IntPtr lpBuffer,
        int lpdwBufferLength);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    private static extern IntPtr SendMessageTimeout(
        IntPtr hWnd,
        int Msg,
        IntPtr wParam,
        string lParam,
        int fuFlags,
        int uTimeout,
        out IntPtr lpdwResult);

    #endregion

    #region INotifyPropertyChanged

    public event PropertyChangedEventHandler? PropertyChanged;

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    #endregion
}

/// <summary>
/// Exception thrown by ProxyService operations.
/// </summary>
public class ProxyException : Exception
{
    public ProxyException(string message) : base(message) { }
    public ProxyException(string message, Exception inner) : base(message, inner) { }
}
