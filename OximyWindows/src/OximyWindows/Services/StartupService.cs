using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using Microsoft.Win32;

namespace OximyWindows.Services;

/// <summary>
/// Manages application auto-start on Windows login via the Registry Run key.
/// </summary>
public class StartupService : INotifyPropertyChanged
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string AppName = "Oximy";

    private bool _isEnabled;
    public bool IsEnabled
    {
        get => _isEnabled;
        private set => SetProperty(ref _isEnabled, value);
    }

    /// <summary>
    /// Auto-enable launch at startup on first run.
    /// Users can still disable this from Settings.
    /// </summary>
    public void CheckAndAutoEnableOnFirstLaunch()
    {
        if (Properties.Settings.Default.InitialAutoEnableDone)
        {
            Debug.WriteLine("[StartupService] Initial auto-enable already done, skipping");
            return;
        }

        // Mark that we've done the initial setup
        Properties.Settings.Default.InitialAutoEnableDone = true;
        Properties.Settings.Default.Save();

        // Only enable if not already enabled
        if (!IsEnabled)
        {
            try
            {
                Enable();
                Debug.WriteLine("[StartupService] Auto-enabled launch at login on first run");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[StartupService] Failed to auto-enable launch at login: {ex.Message}");
            }
        }
        else
        {
            Debug.WriteLine("[StartupService] Launch at login already enabled");
        }
    }

    /// <summary>
    /// Check current startup status.
    /// </summary>
    public void CheckStatus()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath);
            var value = key?.GetValue(AppName) as string;

            // Verify the path points to our executable
            var expectedPath = GetExecutablePath();
            IsEnabled = value != null &&
                       (value.Equals($"\"{expectedPath}\"", StringComparison.OrdinalIgnoreCase) ||
                        value.Equals(expectedPath, StringComparison.OrdinalIgnoreCase));
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Failed to check startup status: {ex.Message}");
            IsEnabled = false;
        }
    }

    /// <summary>
    /// Enable auto-start on login.
    /// </summary>
    public void Enable()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
            if (key == null)
                throw new StartupException("Cannot access Run registry key");

            var exePath = GetExecutablePath();
            key.SetValue(AppName, $"\"{exePath}\"", RegistryValueKind.String);

            // Update settings
            Properties.Settings.Default.LaunchAtStartup = true;
            Properties.Settings.Default.Save();

            IsEnabled = true;
        }
        catch (Exception ex) when (ex is not StartupException)
        {
            throw new StartupException($"Failed to enable startup: {ex.Message}", ex);
        }
    }

    /// <summary>
    /// Disable auto-start on login.
    /// </summary>
    public void Disable()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
            key?.DeleteValue(AppName, throwOnMissingValue: false);

            // Update settings
            Properties.Settings.Default.LaunchAtStartup = false;
            Properties.Settings.Default.Save();

            IsEnabled = false;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Failed to disable startup: {ex.Message}");
            // Don't throw - best effort
        }
    }

    /// <summary>
    /// Toggle auto-start setting.
    /// </summary>
    public void Toggle()
    {
        if (IsEnabled)
            Disable();
        else
            Enable();
    }

    /// <summary>
    /// Get the path to the current executable.
    /// </summary>
    private static string GetExecutablePath()
    {
        return Process.GetCurrentProcess().MainModule?.FileName
            ?? throw new StartupException("Cannot determine executable path");
    }

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
/// Exception thrown by StartupService operations.
/// </summary>
public class StartupException : Exception
{
    public StartupException(string message) : base(message) { }
    public StartupException(string message, Exception inner) : base(message, inner) { }
}
