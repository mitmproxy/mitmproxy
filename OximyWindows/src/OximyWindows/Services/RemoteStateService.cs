using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Timers;
using OximyWindows.Core;
using OximyWindows.Models;

namespace OximyWindows.Services;

/// <summary>
/// App-level feature flags from sensor-config API (delivered via remote-state.json appConfig field).
/// This is the middle tier of the 3-tier config fallback: MDM > API (appConfig) > defaults.
/// </summary>
public class AppConfigFlags
{
    [JsonPropertyName("disableUserLogout")]
    public bool? DisableUserLogout { get; set; }

    [JsonPropertyName("disableQuit")]
    public bool? DisableQuit { get; set; }

    [JsonPropertyName("forceAutoStart")]
    public bool? ForceAutoStart { get; set; }

    [JsonPropertyName("managedSetupComplete")]
    public bool? ManagedSetupComplete { get; set; }

    [JsonPropertyName("managedEnrollmentComplete")]
    public bool? ManagedEnrollmentComplete { get; set; }

    [JsonPropertyName("managedCACertInstalled")]
    public bool? ManagedCACertInstalled { get; set; }

    [JsonPropertyName("managedDeviceToken")]
    public string? ManagedDeviceToken { get; set; }

    [JsonPropertyName("managedDeviceId")]
    public string? ManagedDeviceId { get; set; }

    [JsonPropertyName("managedWorkspaceId")]
    public string? ManagedWorkspaceId { get; set; }

    [JsonPropertyName("managedWorkspaceName")]
    public string? ManagedWorkspaceName { get; set; }

    [JsonPropertyName("apiEndpoint")]
    public string? ApiEndpoint { get; set; }

    [JsonPropertyName("heartbeatInterval")]
    public int? HeartbeatInterval { get; set; }
}

/// <summary>
/// Enforcement rule for an app or website, delivered via remote-state.json.
/// </summary>
public class EnforcementRule
{
    [JsonPropertyName("toolId")]
    public string ToolId { get; set; } = "";

    [JsonPropertyName("toolType")]
    public string ToolType { get; set; } = "";        // "app" | "website"

    [JsonPropertyName("displayName")]
    public string DisplayName { get; set; } = "";

    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "";            // "blocked" | "warn" | "flagged"

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("windowsAppId")]
    public string? WindowsAppId { get; set; }         // process exe name on Windows

    [JsonPropertyName("domain")]
    public string? Domain { get; set; }

    [JsonPropertyName("exemptDeviceIds")]
    public string[]? ExemptDeviceIds { get; set; }
}

/// <summary>
/// Remote state from Python addon (written to ~/.oximy/remote-state.json).
/// The addon writes this file based on server-side configuration.
/// </summary>
public class RemoteState
{
    [JsonPropertyName("sensor_enabled")]
    public bool SensorEnabled { get; set; } = true;

    [JsonPropertyName("force_logout")]
    public bool ForceLogout { get; set; }

    [JsonPropertyName("proxy_active")]
    public bool ProxyActive { get; set; }

    [JsonPropertyName("tenantId")]
    public string? TenantId { get; set; }

    [JsonPropertyName("itSupport")]
    public string? ItSupport { get; set; }

    [JsonPropertyName("timestamp")]
    public string? Timestamp { get; set; }

    [JsonPropertyName("appConfig")]
    public AppConfigFlags? AppConfig { get; set; }

    [JsonPropertyName("enforcementRules")]
    public List<EnforcementRule>? EnforcementRules { get; set; }
}

/// <summary>
/// Service that polls remote-state.json written by the Python addon
/// to reflect admin-controlled monitoring state in the Windows UI.
/// </summary>
public class RemoteStateService : INotifyPropertyChanged, IDisposable
{
    private static RemoteStateService? _instance;
    public static RemoteStateService Instance => _instance ??= new RemoteStateService();

    private readonly System.Timers.Timer _pollTimer;
    private const double PollIntervalMs = 2000; // 2 seconds

    private bool _sensorEnabled = true;
    private bool _proxyActive;
    private string? _tenantId;
    private string? _itSupport;
    private AppConfigFlags? _appConfig;
    private List<EnforcementRule> _enforcementRules = new();
    private DateTime? _lastUpdate;
    private bool _isRunning;
    private bool _disposed;
    private int _isFetchingConfig;  // 0 = idle, 1 = in-flight; use Interlocked for thread safety
    // Deduplication for one-shot commands (prevents re-execution on every poll)
    private bool _lastSeenForceSync;
    private bool _lastSeenClearCache;

    /// <summary>
    /// Whether the sensor is enabled (admin-controlled).
    /// When false, monitoring is paused.
    /// </summary>
    public bool SensorEnabled
    {
        get => _sensorEnabled;
        private set => SetProperty(ref _sensorEnabled, value);
    }

    /// <summary>
    /// Whether the proxy is currently active.
    /// </summary>
    public bool ProxyActive
    {
        get => _proxyActive;
        private set => SetProperty(ref _proxyActive, value);
    }

    /// <summary>
    /// The tenant ID if available.
    /// </summary>
    public string? TenantId
    {
        get => _tenantId;
        private set => SetProperty(ref _tenantId, value);
    }

    /// <summary>
    /// IT support contact information (email or message).
    /// </summary>
    public string? ItSupport
    {
        get => _itSupport;
        private set => SetProperty(ref _itSupport, value);
    }

    /// <summary>
    /// App configuration flags from sensor-config API.
    /// Used as middle tier of 3-tier fallback: MDM > API (appConfig) > defaults.
    /// </summary>
    public AppConfigFlags? AppConfig
    {
        get => _appConfig;
        private set => SetProperty(ref _appConfig, value);
    }

    /// <summary>
    /// Enforcement rules for apps and websites, delivered via remote-state.json.
    /// </summary>
    public List<EnforcementRule> EnforcementRules
    {
        get => _enforcementRules;
        private set => SetProperty(ref _enforcementRules, value);
    }

    /// <summary>
    /// Event fired when enforcement rules change.
    /// </summary>
    public event EventHandler? EnforcementRulesChanged;

    /// <summary>
    /// Last time the state was successfully read.
    /// </summary>
    public DateTime? LastUpdate
    {
        get => _lastUpdate;
        private set => SetProperty(ref _lastUpdate, value);
    }

    /// <summary>
    /// Whether the service is running.
    /// </summary>
    public bool IsRunning
    {
        get => _isRunning;
        private set => SetProperty(ref _isRunning, value);
    }

    /// <summary>
    /// Event fired when sensor_enabled state changes.
    /// </summary>
    public event EventHandler? SensorEnabledChanged;

    /// <summary>
    /// Event fired when force_logout is detected.
    /// </summary>
    public event EventHandler? ForceLogoutRequested;

    private RemoteStateService()
    {
        _pollTimer = new System.Timers.Timer(PollIntervalMs);
        _pollTimer.Elapsed += OnPollTimerElapsed;
        _pollTimer.AutoReset = true;

        // Read initial state
        ReadState();
    }

    /// <summary>
    /// Start polling for remote state.
    /// </summary>
    public void Start()
    {
        if (IsRunning) return;

        IsRunning = true;
        ReadState(); // Initial read
        _pollTimer.Start();

        Debug.WriteLine("[RemoteStateService] Started polling");
    }

    /// <summary>
    /// Stop polling for remote state.
    /// </summary>
    public void Stop()
    {
        _pollTimer.Stop();
        IsRunning = false;

        Debug.WriteLine("[RemoteStateService] Stopped polling");
    }

    private void OnPollTimerElapsed(object? sender, ElapsedEventArgs e)
    {
        ReadState();
    }

    /// <summary>
    /// Read the remote state from the JSON file.
    /// Falls back to direct API fetch when the file is stale or missing.
    /// </summary>
    private void ReadState()
    {
        var filePath = Constants.RemoteStatePath;

        if (!File.Exists(filePath))
        {
            // File doesn't exist — addon may not have started, try direct fetch
            _ = FetchSensorConfigDirectlyAsync();
            return;
        }

        try
        {
            var json = File.ReadAllText(filePath);
            var state = JsonSerializer.Deserialize<RemoteState>(json);

            if (state == null) return;

            var previousEnabled = SensorEnabled;

            SensorEnabled = state.SensorEnabled;
            ProxyActive = state.ProxyActive;
            TenantId = state.TenantId;
            ItSupport = state.ItSupport;
            AppConfig = state.AppConfig;
            LastUpdate = DateTime.Now;

            // Update enforcement rules and fire event if changed
            var newRules = state.EnforcementRules ?? new List<EnforcementRule>();
            if (!RulesEqual(_enforcementRules, newRules))
            {
                EnforcementRules = newRules;
                EnforcementRulesChanged?.Invoke(this, EventArgs.Empty);
            }

            // Update tenant tag if available
            if (!string.IsNullOrEmpty(state.TenantId))
                OximyLogger.SetTag("tenant_id", state.TenantId);

            // Handle state changes
            if (previousEnabled != state.SensorEnabled)
            {
                OximyLogger.Log(EventCode.STATE_STATE_001,
                    state.SensorEnabled ? "Sensor enabled" : "Sensor disabled",
                    new Dictionary<string, object>
                    {
                        ["sensor_enabled"] = state.SensorEnabled,
                        ["previous"] = previousEnabled
                    });
                OximyLogger.SetTag("sensor_enabled", state.SensorEnabled.ToString().ToLowerInvariant());
                Debug.WriteLine($"[RemoteStateService] SensorEnabled changed: {previousEnabled} -> {state.SensorEnabled}");
                SensorEnabledChanged?.Invoke(this, EventArgs.Empty);
            }

            // Handle force_logout command
            if (state.ForceLogout)
            {
                HandleForceLogout();
            }

            // Check if addon's timestamp is stale — fall back to direct API fetch
            if (state.Timestamp != null
                && DateTime.TryParse(state.Timestamp, null, DateTimeStyles.RoundtripKind, out var addonTimestamp))
            {
                var age = DateTime.UtcNow - addonTimestamp;
                if (age.TotalSeconds > Constants.RemoteStateStalenessSeconds)
                {
                    _ = FetchSensorConfigDirectlyAsync();
                }
            }
        }
        catch (JsonException ex)
        {
            OximyLogger.Log(EventCode.STATE_FAIL_201, "Failed to read remote state file",
                new Dictionary<string, object> { ["error"] = ex.Message });
            Debug.WriteLine($"[RemoteStateService] JSON parse error: {ex.Message}");
        }
        catch (IOException ex)
        {
            // File may be locked or in process of being written — don't log every time (too noisy)
            Debug.WriteLine($"[RemoteStateService] IO error: {ex.Message}");
        }
        catch (Exception ex)
        {
            OximyLogger.Log(EventCode.STATE_FAIL_201, "Failed to read remote state file",
                new Dictionary<string, object> { ["error"] = ex.Message });
            Debug.WriteLine($"[RemoteStateService] Unexpected error: {ex.Message}");
        }
    }

    /// <summary>
    /// Fetch sensor-config directly from the API when the addon is not updating remote-state.json.
    /// This keeps appConfig, sensor_enabled, and force_logout current even when the addon is dead.
    /// Also reports command results back to the API so the dashboard shows "executed".
    /// </summary>
    private async Task FetchSensorConfigDirectlyAsync()
    {
        if (Interlocked.CompareExchange(ref _isFetchingConfig, 1, 0) != 0) return;
        if (AppState.Instance.Phase != Phase.Connected)
        {
            Interlocked.Exchange(ref _isFetchingConfig, 0);
            return;
        }

        try
        {
            var data = await APIClient.Instance.FetchSensorConfigAsync();
            if (data == null) return;

            var previousEnabled = SensorEnabled;
            var commandResults = new Dictionary<string, CommandResult>();
            var now = DateTime.UtcNow.ToString("o");

            if (data.Commands != null)
            {
                SensorEnabled = data.Commands.SensorEnabled;

                // Report sensor_enabled result when state actually changed
                if (previousEnabled != data.Commands.SensorEnabled)
                {
                    commandResults["sensor_enabled"] = new CommandResult
                    {
                        Success = true,
                        ExecutedAt = now
                    };
                }

                if (data.Commands.ForceLogout)
                {
                    HandleForceLogout();
                    commandResults["force_logout"] = new CommandResult
                    {
                        Success = true,
                        ExecutedAt = now
                    };
                }

                // Handle force_sync (one-shot: only execute on false→true transition)
                if (data.Commands.ForceSync && !_lastSeenForceSync)
                {
                    Debug.WriteLine("[RemoteStateService] Executing force_sync via direct fetch");
                    try
                    {
                        await SyncService.Instance.SyncNowAsync();
                        commandResults["force_sync"] = new CommandResult
                        {
                            Success = true,
                            ExecutedAt = now
                        };
                    }
                    catch (Exception ex)
                    {
                        commandResults["force_sync"] = new CommandResult
                        {
                            Success = false,
                            ExecutedAt = now,
                            Error = ex.Message
                        };
                    }
                }
                _lastSeenForceSync = data.Commands.ForceSync;

                // Handle clear_cache (one-shot: only execute on false→true transition)
                if (data.Commands.ClearCache && !_lastSeenClearCache)
                {
                    Debug.WriteLine("[RemoteStateService] Executing clear_cache via direct fetch");
                    try
                    {
                        SyncService.Instance.ClearLocalData();
                        commandResults["clear_cache"] = new CommandResult
                        {
                            Success = true,
                            ExecutedAt = now
                        };
                    }
                    catch (Exception ex)
                    {
                        commandResults["clear_cache"] = new CommandResult
                        {
                            Success = false,
                            ExecutedAt = now,
                            Error = ex.Message
                        };
                    }
                }
                _lastSeenClearCache = data.Commands.ClearCache;
            }

            if (data.AppConfig != null)
                AppConfig = data.AppConfig;

            if (!string.IsNullOrEmpty(data.TenantId))
            {
                TenantId = data.TenantId;
                OximyLogger.SetTag("tenant_id", data.TenantId);
            }

            if (!string.IsNullOrEmpty(data.ItSupport))
                ItSupport = data.ItSupport;

            // Update enforcement rules from direct API fetch
            if (data.EnforcementRules != null)
            {
                var newRules = data.EnforcementRules;
                if (!RulesEqual(_enforcementRules, newRules))
                {
                    EnforcementRules = newRules;
                    EnforcementRulesChanged?.Invoke(this, EventArgs.Empty);
                    Debug.WriteLine($"[RemoteStateService] Enforcement rules updated via direct fetch ({newRules.Count} rules)");
                }
            }

            LastUpdate = DateTime.Now;

            if (previousEnabled != SensorEnabled)
            {
                OximyLogger.Log(EventCode.STATE_STATE_001,
                    SensorEnabled ? "Sensor enabled (direct fetch)" : "Sensor disabled (direct fetch)",
                    new Dictionary<string, object>
                    {
                        ["sensor_enabled"] = SensorEnabled,
                        ["previous"] = previousEnabled,
                        ["source"] = "direct_api"
                    });
                OximyLogger.SetTag("sensor_enabled", SensorEnabled.ToString().ToLowerInvariant());
                Debug.WriteLine($"[RemoteStateService] SensorEnabled changed via direct fetch: {previousEnabled} -> {SensorEnabled}");
                SensorEnabledChanged?.Invoke(this, EventArgs.Empty);
            }

            // POST command results back to API so dashboard shows "executed"
            if (commandResults.Count > 0)
            {
                _ = APIClient.Instance.PostCommandResultsAsync(commandResults);
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[RemoteStateService] Direct sensor-config fetch failed: {ex.Message}");
        }
        finally
        {
            Interlocked.Exchange(ref _isFetchingConfig, 0);
        }
    }

    /// <summary>
    /// Compare two enforcement rule lists by toolId+mode for change detection.
    /// </summary>
    private static bool RulesEqual(List<EnforcementRule> a, List<EnforcementRule> b)
    {
        if (a.Count != b.Count) return false;
        for (int i = 0; i < a.Count; i++)
        {
            if (a[i].ToolId != b[i].ToolId
                || a[i].ToolType != b[i].ToolType
                || a[i].Mode != b[i].Mode
                || a[i].DisplayName != b[i].DisplayName
                || a[i].WindowsAppId != b[i].WindowsAppId
                || a[i].Domain != b[i].Domain
                || a[i].Message != b[i].Message
                || !ExemptionsEqual(a[i].ExemptDeviceIds, b[i].ExemptDeviceIds))
                return false;
        }
        return true;
    }

    private static bool ExemptionsEqual(string[]? a, string[]? b)
    {
        if (a is null && b is null) return true;
        if (a is null || b is null) return false;
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++)
        {
            if (a[i] != b[i]) return false;
        }
        return true;
    }

    /// <summary>
    /// Handle force logout command from server.
    /// </summary>
    private void HandleForceLogout()
    {
        OximyLogger.Log(EventCode.STATE_CMD_003, "Force logout received");
        Debug.WriteLine("[RemoteStateService] Force logout command received");

        // Clear the force_logout flag by deleting the file
        // (addon will recreate it on next config fetch)
        try
        {
            File.Delete(Constants.RemoteStatePath);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[RemoteStateService] Failed to delete state file: {ex.Message}");
        }

        // Trigger logout
        ForceLogoutRequested?.Invoke(this, EventArgs.Empty);
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

    #region IDisposable

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        Stop();
        _pollTimer.Dispose();
    }

    #endregion
}
