using System.ComponentModel;
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
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey, writable: true);
            if (key == null)
                throw new ProxyException("Cannot access Internet Settings registry key");

            // Store original values for rollback
            _originalProxyEnable = key.GetValue("ProxyEnable") as int?;
            _originalProxyServer = key.GetValue("ProxyServer") as string;
            _originalProxyOverride = key.GetValue("ProxyOverride") as string;

            // Set new proxy values
            key.SetValue("ProxyEnable", 1, RegistryValueKind.DWord);
            key.SetValue("ProxyServer", $"127.0.0.1:{port}", RegistryValueKind.String);
            key.SetValue("ProxyOverride", Constants.ProxyBypassList, RegistryValueKind.String);

            // Notify Windows and applications of the change
            NotifySettingsChange();

            IsProxyEnabled = true;
            ConfiguredPort = port;
        }
        catch (Exception ex) when (ex is not ProxyException)
        {
            throw new ProxyException($"Failed to enable proxy: {ex.Message}", ex);
        }
    }

    /// <summary>
    /// Disable the system proxy.
    /// </summary>
    public void DisableProxy()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(InternetSettingsKey, writable: true);
            if (key == null)
                return;

            // Restore original values or just disable
            if (_originalProxyEnable.HasValue)
            {
                key.SetValue("ProxyEnable", _originalProxyEnable.Value, RegistryValueKind.DWord);

                if (_originalProxyServer != null)
                    key.SetValue("ProxyServer", _originalProxyServer, RegistryValueKind.String);
                else
                    key.DeleteValue("ProxyServer", throwOnMissingValue: false);

                if (_originalProxyOverride != null)
                    key.SetValue("ProxyOverride", _originalProxyOverride, RegistryValueKind.String);
            }
            else
            {
                // Just disable if we don't have original values
                key.SetValue("ProxyEnable", 0, RegistryValueKind.DWord);
            }

            NotifySettingsChange();

            IsProxyEnabled = false;
            ConfiguredPort = null;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to disable proxy: {ex.Message}");
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
