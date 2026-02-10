using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using Microsoft.Win32;

namespace OximyWindows.Services;

/// <summary>
/// Service to detect and read MDM-managed configuration from Windows Registry.
/// MDM solutions (Intune, SCCM, etc.) can deploy configuration via Group Policy
/// or custom OMA-URI settings to HKLM\SOFTWARE\Policies\Oximy\.
///
/// This mirrors the macOS MDMConfigService which reads from /Library/Managed Preferences/.
/// </summary>
public class MDMConfigService : INotifyPropertyChanged
{
    private static MDMConfigService? _instance;
    public static MDMConfigService Instance => _instance ??= new MDMConfigService();

    private const string PolicyKeyPath = @"SOFTWARE\Policies\Oximy";

    // Managed Preference Keys (matching macOS names for consistency)
    private const string KeyDeviceToken = "ManagedDeviceToken";
    private const string KeyDeviceId = "ManagedDeviceId";
    private const string KeyWorkspaceId = "ManagedWorkspaceId";
    private const string KeyWorkspaceName = "ManagedWorkspaceName";
    private const string KeySetupComplete = "ManagedSetupComplete";
    private const string KeyEnrollmentComplete = "ManagedEnrollmentComplete";
    private const string KeyCACertInstalled = "ManagedCACertInstalled";
    private const string KeyForceAutoStart = "ForceAutoStart";
    private const string KeyDisableUserLogout = "DisableUserLogout";
    private const string KeyDisableQuit = "DisableQuit";
    private const string KeyAPIEndpoint = "APIEndpoint";
    private const string KeyHeartbeatInterval = "HeartbeatInterval";

    private bool _isManagedDevice;
    /// <summary>
    /// Whether this device has MDM configuration deployed.
    /// </summary>
    public bool IsManagedDevice
    {
        get => _isManagedDevice;
        private set => SetProperty(ref _isManagedDevice, value);
    }

    private DateTime? _lastConfigCheck;
    /// <summary>
    /// When the MDM configuration was last checked.
    /// </summary>
    public DateTime? LastConfigCheck
    {
        get => _lastConfigCheck;
        private set => SetProperty(ref _lastConfigCheck, value);
    }

    // Cached configuration values
    private string? _managedDeviceToken;
    private string? _managedDeviceId;
    private string? _managedWorkspaceId;
    private string? _managedWorkspaceName;
    private bool _managedSetupComplete;
    private bool _managedEnrollmentComplete;
    private bool _managedCACertInstalled;
    private bool _forceAutoStart;
    private bool _disableUserLogout;
    private bool _disableQuit;
    private string? _apiEndpoint;
    private int? _heartbeatInterval;

    // MARK: - Credential Accessors (with 3-tier fallback: MDM > API > default)

    /// <summary>
    /// Pre-provisioned device API token.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public string? ManagedDeviceToken
    {
        get
        {
            if (!string.IsNullOrEmpty(_managedDeviceToken)) return _managedDeviceToken;
            if (!string.IsNullOrEmpty(RemoteStateService.Instance.AppConfig?.ManagedDeviceToken)) return RemoteStateService.Instance.AppConfig.ManagedDeviceToken;
            return null;
        }
    }

    /// <summary>
    /// Pre-assigned device identifier.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public string? ManagedDeviceId
    {
        get
        {
            if (!string.IsNullOrEmpty(_managedDeviceId)) return _managedDeviceId;
            if (!string.IsNullOrEmpty(RemoteStateService.Instance.AppConfig?.ManagedDeviceId)) return RemoteStateService.Instance.AppConfig.ManagedDeviceId;
            return null;
        }
    }

    /// <summary>
    /// Organization workspace ID.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public string? ManagedWorkspaceId
    {
        get
        {
            if (!string.IsNullOrEmpty(_managedWorkspaceId)) return _managedWorkspaceId;
            if (!string.IsNullOrEmpty(RemoteStateService.Instance.AppConfig?.ManagedWorkspaceId)) return RemoteStateService.Instance.AppConfig.ManagedWorkspaceId;
            return null;
        }
    }

    /// <summary>
    /// Display name for workspace.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public string? ManagedWorkspaceName
    {
        get
        {
            if (!string.IsNullOrEmpty(_managedWorkspaceName)) return _managedWorkspaceName;
            if (!string.IsNullOrEmpty(RemoteStateService.Instance.AppConfig?.ManagedWorkspaceName)) return RemoteStateService.Instance.AppConfig.ManagedWorkspaceName;
            return null;
        }
    }

    // MARK: - Setup Bypass Accessors (with 3-tier fallback)

    /// <summary>
    /// Skip all setup UI (enrollment + certificate + proxy).
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool ManagedSetupComplete
    {
        get
        {
            if (_isManagedDevice && _managedSetupComplete) return true;
            if (RemoteStateService.Instance.AppConfig?.ManagedSetupComplete == true) return true;
            return false;
        }
    }

    /// <summary>
    /// Skip enrollment UI only.
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool ManagedEnrollmentComplete
    {
        get
        {
            if (_isManagedDevice && _managedEnrollmentComplete) return true;
            if (RemoteStateService.Instance.AppConfig?.ManagedEnrollmentComplete == true) return true;
            return false;
        }
    }

    /// <summary>
    /// CA certificate was deployed via MDM.
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool ManagedCACertInstalled
    {
        get
        {
            if (_isManagedDevice && _managedCACertInstalled) return true;
            if (RemoteStateService.Instance.AppConfig?.ManagedCACertInstalled == true) return true;
            return false;
        }
    }

    // MARK: - Lockdown Control Accessors (with 3-tier fallback)

    /// <summary>
    /// Prevent user from disabling auto-start.
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool ForceAutoStart
    {
        get
        {
            if (_isManagedDevice && _forceAutoStart) return true;
            if (RemoteStateService.Instance.AppConfig?.ForceAutoStart == true) return true;
            return false;
        }
    }

    /// <summary>
    /// Hide logout option in UI.
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool DisableUserLogout
    {
        get
        {
            if (_isManagedDevice && _disableUserLogout) return true;
            if (RemoteStateService.Instance.AppConfig?.DisableUserLogout == true) return true;
            return false;
        }
    }

    /// <summary>
    /// Prevent app termination.
    /// Priority: MDM > remote-state (API) > default (false)
    /// </summary>
    public bool DisableQuit
    {
        get
        {
            if (_isManagedDevice && _disableQuit) return true;
            if (RemoteStateService.Instance.AppConfig?.DisableQuit == true) return true;
            return false;
        }
    }

    // MARK: - Configuration Accessors (with 3-tier fallback)

    /// <summary>
    /// Custom API URL override.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public string? APIEndpoint
    {
        get
        {
            if (!string.IsNullOrEmpty(_apiEndpoint)) return _apiEndpoint;
            if (!string.IsNullOrEmpty(RemoteStateService.Instance.AppConfig?.ApiEndpoint)) return RemoteStateService.Instance.AppConfig.ApiEndpoint;
            return null;
        }
    }

    /// <summary>
    /// Heartbeat interval override in seconds.
    /// Priority: MDM > remote-state (API) > default (null)
    /// </summary>
    public int? HeartbeatInterval
    {
        get
        {
            if (_isManagedDevice && _heartbeatInterval.HasValue && _heartbeatInterval.Value > 0) return _heartbeatInterval;
            if (RemoteStateService.Instance.AppConfig?.HeartbeatInterval is > 0) return RemoteStateService.Instance.AppConfig.HeartbeatInterval;
            return null;
        }
    }

    /// <summary>
    /// Whether the app should skip all setup UI and go directly to Connected phase.
    /// Requires ManagedSetupComplete=true AND a valid device token.
    /// </summary>
    public bool ShouldSkipAllSetup => ManagedSetupComplete && !string.IsNullOrEmpty(ManagedDeviceToken);

    /// <summary>
    /// Whether the app should skip enrollment UI (but still show setup for cert/proxy).
    /// </summary>
    public bool ShouldSkipEnrollment => (ManagedEnrollmentComplete || ManagedSetupComplete) && !string.IsNullOrEmpty(ManagedDeviceToken);

    private MDMConfigService()
    {
        CheckManagedStatus();
    }

    /// <summary>
    /// Check if this device has MDM configuration and load values.
    /// Called at startup and can be called to refresh.
    /// </summary>
    public void CheckManagedStatus()
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(PolicyKeyPath);

            if (key == null)
            {
                // No MDM configuration present
                IsManagedDevice = false;
                ClearCachedValues();
                Debug.WriteLine("[MDMConfigService] No MDM configuration found");
                LastConfigCheck = DateTime.UtcNow;
                return;
            }

            // MDM configuration exists - load all values
            IsManagedDevice = true;

            _managedDeviceToken = ReadStringValue(key, KeyDeviceToken);
            _managedDeviceId = ReadStringValue(key, KeyDeviceId);
            _managedWorkspaceId = ReadStringValue(key, KeyWorkspaceId);
            _managedWorkspaceName = ReadStringValue(key, KeyWorkspaceName);
            _managedSetupComplete = ReadBoolValue(key, KeySetupComplete);
            _managedEnrollmentComplete = ReadBoolValue(key, KeyEnrollmentComplete);
            _managedCACertInstalled = ReadBoolValue(key, KeyCACertInstalled);
            _forceAutoStart = ReadBoolValue(key, KeyForceAutoStart);
            _disableUserLogout = ReadBoolValue(key, KeyDisableUserLogout);
            _disableQuit = ReadBoolValue(key, KeyDisableQuit);
            _apiEndpoint = ReadStringValue(key, KeyAPIEndpoint);
            _heartbeatInterval = ReadIntValue(key, KeyHeartbeatInterval);

            LastConfigCheck = DateTime.UtcNow;

            Debug.WriteLine($"[MDMConfigService] MDM configuration loaded:");
            Debug.WriteLine($"  - ManagedDeviceToken: {(string.IsNullOrEmpty(_managedDeviceToken) ? "(not set)" : "(set)")}");
            Debug.WriteLine($"  - ManagedDeviceId: {_managedDeviceId ?? "(not set)"}");
            Debug.WriteLine($"  - ManagedWorkspaceName: {_managedWorkspaceName ?? "(not set)"}");
            Debug.WriteLine($"  - ManagedSetupComplete: {_managedSetupComplete}");
            Debug.WriteLine($"  - ManagedEnrollmentComplete: {_managedEnrollmentComplete}");
            Debug.WriteLine($"  - ForceAutoStart: {_forceAutoStart}");
            Debug.WriteLine($"  - DisableUserLogout: {_disableUserLogout}");
            Debug.WriteLine($"  - DisableQuit: {_disableQuit}");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MDMConfigService] Error reading MDM configuration: {ex.Message}");
            IsManagedDevice = false;
            ClearCachedValues();
        }
    }

    /// <summary>
    /// Apply MDM configuration to the app's standard settings.
    /// Called after CheckManagedStatus() when IsManagedDevice is true.
    /// </summary>
    public void ApplyManagedConfiguration()
    {
        if (!IsManagedDevice)
        {
            Debug.WriteLine("[MDMConfigService] Cannot apply - not a managed device");
            return;
        }

        var settings = Properties.Settings.Default;

        // Apply workspace info if provided
        if (!string.IsNullOrEmpty(_managedWorkspaceName))
        {
            settings.WorkspaceName = _managedWorkspaceName;
            Debug.WriteLine($"[MDMConfigService] Applied WorkspaceName: {_managedWorkspaceName}");
        }

        if (!string.IsNullOrEmpty(_managedWorkspaceId))
        {
            settings.WorkspaceId = _managedWorkspaceId;
            Debug.WriteLine($"[MDMConfigService] Applied WorkspaceId: {_managedWorkspaceId}");
        }

        if (!string.IsNullOrEmpty(_managedDeviceId))
        {
            settings.DeviceId = _managedDeviceId;
            Debug.WriteLine($"[MDMConfigService] Applied DeviceId: {_managedDeviceId}");
        }

        // Apply device token (also triggers token file write in AppState)
        if (!string.IsNullOrEmpty(_managedDeviceToken))
        {
            settings.DeviceToken = _managedDeviceToken;
            Debug.WriteLine("[MDMConfigService] Applied DeviceToken");
        }

        // Mark setup complete if MDM says so
        if (_managedSetupComplete)
        {
            settings.SetupComplete = true;
            Debug.WriteLine("[MDMConfigService] Marked SetupComplete=true");
        }

        settings.Save();
        Debug.WriteLine("[MDMConfigService] Settings saved");
    }

    /// <summary>
    /// Read a string value from registry.
    /// </summary>
    private static string? ReadStringValue(RegistryKey key, string valueName)
    {
        try
        {
            var value = key.GetValue(valueName);
            return value as string;
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Read a boolean value from registry (stored as DWORD, 1=true, 0=false).
    /// </summary>
    private static bool ReadBoolValue(RegistryKey key, string valueName)
    {
        try
        {
            var value = key.GetValue(valueName);
            if (value is int intValue)
                return intValue == 1;
            return false;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// Read an integer value from registry.
    /// </summary>
    private static int? ReadIntValue(RegistryKey key, string valueName)
    {
        try
        {
            var value = key.GetValue(valueName);
            if (value is int intValue)
                return intValue;
            return null;
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Clear all cached values when MDM is not present.
    /// </summary>
    private void ClearCachedValues()
    {
        _managedDeviceToken = null;
        _managedDeviceId = null;
        _managedWorkspaceId = null;
        _managedWorkspaceName = null;
        _managedSetupComplete = false;
        _managedEnrollmentComplete = false;
        _managedCACertInstalled = false;
        _forceAutoStart = false;
        _disableUserLogout = false;
        _disableQuit = false;
        _apiEndpoint = null;
        _heartbeatInterval = null;
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
