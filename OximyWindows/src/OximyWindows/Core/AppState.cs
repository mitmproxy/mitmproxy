using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;

namespace OximyWindows.Core;

/// <summary>
/// Global application state management.
/// Implements singleton pattern with observable properties.
/// Matches the Mac app's three-phase flow: Enrollment -> Setup -> Ready
/// </summary>
public class AppState : INotifyPropertyChanged
{
    private static AppState? _instance;
    public static AppState Instance => _instance ??= new AppState();

    private Phase _phase = Phase.Enrollment;
    public Phase Phase
    {
        get => _phase;
        private set => SetProperty(ref _phase, value);
    }

    private ConnectionStatus _connectionStatus = ConnectionStatus.Disconnected;
    public ConnectionStatus ConnectionStatus
    {
        get => _connectionStatus;
        set => SetProperty(ref _connectionStatus, value);
    }

    private string _deviceName = Environment.MachineName;
    public string DeviceName
    {
        get => _deviceName;
        set => SetProperty(ref _deviceName, value);
    }

    private string _workspaceName = string.Empty;
    public string WorkspaceName
    {
        get => _workspaceName;
        set => SetProperty(ref _workspaceName, value);
    }

    private string _workspaceId = string.Empty;
    public string WorkspaceId
    {
        get => _workspaceId;
        private set => SetProperty(ref _workspaceId, value);
    }

    private string _deviceId = string.Empty;
    public string DeviceId
    {
        get => _deviceId;
        private set => SetProperty(ref _deviceId, value);
    }

    private string _deviceToken = string.Empty;
    public string DeviceToken
    {
        get => _deviceToken;
        private set => SetProperty(ref _deviceToken, value);
    }

    private int _currentPort = Constants.PreferredPort;
    public int CurrentPort
    {
        get => _currentPort;
        set => SetProperty(ref _currentPort, value);
    }

    private int _eventsCapturedToday;
    public int EventsCapturedToday
    {
        get => _eventsCapturedToday;
        set => SetProperty(ref _eventsCapturedToday, value);
    }

    private int _eventsPending;
    public int EventsPending
    {
        get => _eventsPending;
        set => SetProperty(ref _eventsPending, value);
    }

    private DateTime? _lastSyncTime;
    public DateTime? LastSyncTime
    {
        get => _lastSyncTime;
        set => SetProperty(ref _lastSyncTime, value);
    }

    private string _errorMessage = string.Empty;
    public string ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    private bool _isSetupCertificateComplete;
    public bool IsSetupCertificateComplete
    {
        get => _isSetupCertificateComplete;
        set => SetProperty(ref _isSetupCertificateComplete, value);
    }

    private bool _isSetupProxyComplete;
    public bool IsSetupProxyComplete
    {
        get => _isSetupProxyComplete;
        set => SetProperty(ref _isSetupProxyComplete, value);
    }

    private AppState()
    {
        LoadPersistedState();
    }

    /// <summary>
    /// Load persisted state from settings.
    /// </summary>
    private void LoadPersistedState()
    {
        var settings = Properties.Settings.Default;

        DeviceName = string.IsNullOrEmpty(settings.DeviceName)
            ? Environment.MachineName
            : settings.DeviceName;

        // Load saved credentials
        if (!string.IsNullOrEmpty(settings.DeviceToken))
        {
            DeviceToken = settings.DeviceToken;
            DeviceId = settings.DeviceId;
            WorkspaceName = settings.WorkspaceName;
            WorkspaceId = settings.WorkspaceId;

            // Always go to Connected if we have a token (setup happens in background)
            Phase = Phase.Connected;

            // Ensure token file exists for Python addon (handles upgrade from older versions)
            WriteDeviceTokenFile(settings.DeviceToken);
        }
        else
        {
            Phase = Phase.Enrollment;
        }

        // Update events count
        EventsCapturedToday = Constants.CountTodayEvents();
    }

    /// <summary>
    /// Complete enrollment with device registration response.
    /// Transitions directly to Connected phase (setup happens in background).
    /// </summary>
    public void CompleteEnrollment(string deviceId, string deviceToken, string workspaceName, string workspaceId)
    {
        var settings = Properties.Settings.Default;
        settings.DeviceId = deviceId;
        settings.DeviceToken = deviceToken;
        settings.WorkspaceName = workspaceName;
        settings.WorkspaceId = workspaceId;
        settings.SetupComplete = true;  // Mark setup complete immediately
        settings.Save();

        DeviceId = deviceId;
        DeviceToken = deviceToken;
        WorkspaceName = workspaceName;
        WorkspaceId = workspaceId;
        Phase = Phase.Connected;  // Go directly to Connected (skip Setup)

        // Write device token to file for Python addon to read
        WriteDeviceTokenFile(deviceToken);
    }

    /// <summary>
    /// Write device token to ~/.oximy/device-token file for Python addon.
    /// </summary>
    private static void WriteDeviceTokenFile(string token)
    {
        try
        {
            var tokenPath = Path.Combine(Constants.OximyDir, "device-token");
            Directory.CreateDirectory(Constants.OximyDir);
            File.WriteAllText(tokenPath, token);
            System.Diagnostics.Debug.WriteLine($"[AppState] Device token written to {tokenPath}");
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[AppState] Failed to write device token file: {ex.Message}");
        }
    }

    /// <summary>
    /// Mark certificate setup as complete.
    /// </summary>
    public void CompleteCertificateSetup()
    {
        IsSetupCertificateComplete = true;
        CheckSetupComplete();
    }

    /// <summary>
    /// Mark proxy setup as complete.
    /// </summary>
    public void CompleteProxySetup()
    {
        IsSetupProxyComplete = true;
        CheckSetupComplete();
    }

    /// <summary>
    /// Check if all setup steps are complete and transition to Connected phase.
    /// </summary>
    private void CheckSetupComplete()
    {
        if (IsSetupCertificateComplete && IsSetupProxyComplete)
        {
            var settings = Properties.Settings.Default;
            settings.SetupComplete = true;
            settings.Save();

            Phase = Phase.Connected;
        }
    }

    /// <summary>
    /// Complete the entire setup and transition to Connected phase.
    /// </summary>
    public void CompleteSetup()
    {
        var settings = Properties.Settings.Default;
        settings.SetupComplete = true;
        settings.Save();

        IsSetupCertificateComplete = true;
        IsSetupProxyComplete = true;
        Phase = Phase.Connected;
    }

    /// <summary>
    /// Skip setup for now (set up later).
    /// </summary>
    public void SkipSetup()
    {
        Phase = Phase.Connected;
    }

    /// <summary>
    /// Complete login with workspace credentials (legacy method for compatibility).
    /// </summary>
    public void CompleteLogin(string workspaceName, string deviceToken)
    {
        var settings = Properties.Settings.Default;
        settings.WorkspaceName = workspaceName;
        settings.DeviceToken = deviceToken;
        settings.Save();

        WorkspaceName = workspaceName;
        DeviceToken = deviceToken;
        Phase = Phase.Connected;
    }

    /// <summary>
    /// Log out and return to enrollment phase.
    /// </summary>
    public void Logout()
    {
        var settings = Properties.Settings.Default;
        settings.DeviceToken = string.Empty;
        settings.DeviceId = string.Empty;
        settings.WorkspaceName = string.Empty;
        settings.WorkspaceId = string.Empty;
        settings.SetupComplete = false;
        settings.Save();

        DeviceToken = string.Empty;
        DeviceId = string.Empty;
        WorkspaceName = string.Empty;
        WorkspaceId = string.Empty;
        IsSetupCertificateComplete = false;
        IsSetupProxyComplete = false;
        Phase = Phase.Enrollment;

        // Remove device token file
        DeleteDeviceTokenFile();
    }

    /// <summary>
    /// Delete the device token file on logout.
    /// </summary>
    private static void DeleteDeviceTokenFile()
    {
        try
        {
            var tokenPath = Path.Combine(Constants.OximyDir, "device-token");
            if (File.Exists(tokenPath))
            {
                File.Delete(tokenPath);
                System.Diagnostics.Debug.WriteLine($"[AppState] Device token file deleted");
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[AppState] Failed to delete device token file: {ex.Message}");
        }
    }

    /// <summary>
    /// Reset to initial enrollment state.
    /// </summary>
    public void Reset()
    {
        Logout();
    }

    /// <summary>
    /// Complete the onboarding phase (legacy).
    /// </summary>
    public void CompleteOnboarding()
    {
        Phase = Phase.Enrollment;
    }

    /// <summary>
    /// Complete the permissions phase (legacy).
    /// </summary>
    public void CompletePermissions()
    {
        Phase = Phase.Connected;
    }

    /// <summary>
    /// Reset to initial onboarding state (legacy).
    /// </summary>
    public void ResetOnboarding()
    {
        Reset();
    }

    /// <summary>
    /// Update device name.
    /// </summary>
    public void UpdateDeviceName(string name)
    {
        var settings = Properties.Settings.Default;
        settings.DeviceName = name;
        settings.Save();

        DeviceName = name;
    }

    /// <summary>
    /// Refresh events count.
    /// </summary>
    public void RefreshEventsCount()
    {
        EventsCapturedToday = Constants.CountTodayEvents();
    }

    /// <summary>
    /// Get relative time string for last sync.
    /// </summary>
    public string GetLastSyncRelativeTime()
    {
        if (!LastSyncTime.HasValue)
            return "Never";

        var elapsed = DateTime.UtcNow - LastSyncTime.Value;

        if (elapsed.TotalSeconds < 60)
            return "Just now";
        if (elapsed.TotalMinutes < 60)
            return $"{(int)elapsed.TotalMinutes} min ago";
        if (elapsed.TotalHours < 24)
            return $"{(int)elapsed.TotalHours} hours ago";

        return $"{(int)elapsed.TotalDays} days ago";
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

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    #endregion
}
