using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace OximyWindows.Core;

/// <summary>
/// Global application state management.
/// Implements singleton pattern with observable properties.
/// </summary>
public class AppState : INotifyPropertyChanged
{
    private static AppState? _instance;
    public static AppState Instance => _instance ??= new AppState();

    private Phase _phase = Phase.Onboarding;
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

    private string _errorMessage = string.Empty;
    public string ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
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

        if (settings.OnboardingComplete)
        {
            if (!string.IsNullOrEmpty(settings.DeviceToken))
            {
                WorkspaceName = settings.WorkspaceName;
                DeviceToken = settings.DeviceToken;
                Phase = Phase.Connected;
            }
            else
            {
                Phase = Phase.Login;
            }
        }
        else
        {
            Phase = Phase.Onboarding;
        }

        // Update events count
        EventsCapturedToday = Constants.CountTodayEvents();
    }

    /// <summary>
    /// Complete the onboarding phase.
    /// </summary>
    public void CompleteOnboarding()
    {
        var settings = Properties.Settings.Default;
        settings.OnboardingComplete = true;
        settings.Save();

        Phase = Phase.Permissions;
    }

    /// <summary>
    /// Complete the permissions phase.
    /// </summary>
    public void CompletePermissions()
    {
        Phase = Phase.Login;
    }

    /// <summary>
    /// Complete login with workspace credentials.
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
    /// Log out and return to login phase.
    /// </summary>
    public void Logout()
    {
        var settings = Properties.Settings.Default;
        settings.DeviceToken = string.Empty;
        settings.WorkspaceName = string.Empty;
        settings.Save();

        WorkspaceName = string.Empty;
        DeviceToken = string.Empty;
        Phase = Phase.Login;
    }

    /// <summary>
    /// Reset to initial onboarding state.
    /// </summary>
    public void ResetOnboarding()
    {
        var settings = Properties.Settings.Default;
        settings.OnboardingComplete = false;
        settings.DeviceToken = string.Empty;
        settings.WorkspaceName = string.Empty;
        settings.Save();

        WorkspaceName = string.Empty;
        DeviceToken = string.Empty;
        Phase = Phase.Onboarding;
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
