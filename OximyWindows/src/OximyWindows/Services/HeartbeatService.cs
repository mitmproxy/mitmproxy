using System.Diagnostics;
using System.IO;
using System.Text.Json;
using OximyWindows.Core;
using OximyWindows.Models;

namespace OximyWindows.Services;

/// <summary>
/// Service for sending periodic heartbeats to the backend.
/// Collects system metrics and processes server commands.
/// </summary>
public class HeartbeatService : IDisposable
{
    private static HeartbeatService? _instance;
    public static HeartbeatService Instance => _instance ??= new HeartbeatService();

    private Timer? _heartbeatTimer;
    private int _heartbeatIntervalMs;
    private bool _disposed;
    private readonly object _lock = new();
    private int _healthCheckCounter;

    public event EventHandler? SyncRequested;
    public event EventHandler? RestartProxyRequested;
    public event EventHandler? DisableProxyRequested;
    public event EventHandler? LogoutRequested;

    private HeartbeatService()
    {
        _heartbeatIntervalMs = Constants.DefaultHeartbeatIntervalSeconds * 1000;

        // Subscribe to API events
        APIClient.Instance.AuthenticationFailed += OnAuthenticationFailed;
        APIClient.Instance.WorkspaceNameUpdated += OnWorkspaceNameUpdated;
    }

    /// <summary>
    /// Start the heartbeat timer.
    /// </summary>
    public void Start()
    {
        lock (_lock)
        {
            if (_heartbeatTimer != null)
                return;

            Debug.WriteLine($"[HeartbeatService] Starting with interval {_heartbeatIntervalMs}ms");

            _heartbeatTimer = new Timer(
                OnHeartbeatTick,
                null,
                TimeSpan.FromSeconds(5), // Initial delay
                TimeSpan.FromMilliseconds(_heartbeatIntervalMs));
        }
    }

    /// <summary>
    /// Stop the heartbeat timer.
    /// </summary>
    public void Stop()
    {
        lock (_lock)
        {
            _heartbeatTimer?.Dispose();
            _heartbeatTimer = null;
            Debug.WriteLine("[HeartbeatService] Stopped");
        }
    }

    /// <summary>
    /// Update the heartbeat interval (called when config is received from server).
    /// </summary>
    public void UpdateInterval(int intervalSeconds)
    {
        lock (_lock)
        {
            _heartbeatIntervalMs = intervalSeconds * 1000;

            if (_heartbeatTimer != null)
            {
                _heartbeatTimer.Change(
                    TimeSpan.FromMilliseconds(_heartbeatIntervalMs),
                    TimeSpan.FromMilliseconds(_heartbeatIntervalMs));

                Debug.WriteLine($"[HeartbeatService] Updated interval to {intervalSeconds}s");
            }
        }
    }

    /// <summary>
    /// Read command execution results from file (written by Python addon).
    /// Results are included in the next heartbeat and the file is deleted after reading.
    /// </summary>
    private static Dictionary<string, CommandResult>? ReadCommandResults()
    {
        var path = Path.Combine(Constants.OximyDir, "command-results.json");
        if (!File.Exists(path)) return null;

        try
        {
            var json = File.ReadAllText(path);
            var rawResults = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);
            if (rawResults == null || rawResults.Count == 0) return null;

            var results = new Dictionary<string, CommandResult>();
            foreach (var (key, value) in rawResults)
            {
                var success = value.TryGetProperty("success", out var successProp) && successProp.GetBoolean();
                var executedAt = value.TryGetProperty("executedAt", out var executedAtProp) ? executedAtProp.GetString() ?? "" : "";
                string? error = value.TryGetProperty("error", out var errorProp) && errorProp.ValueKind != JsonValueKind.Null ? errorProp.GetString() : null;

                results[key] = new CommandResult
                {
                    Success = success,
                    ExecutedAt = executedAt,
                    Error = error
                };
            }

            // Delete file after reading (consumed by heartbeat)
            try { File.Delete(path); } catch { /* ignore */ }

            if (results.Count > 0)
            {
                Debug.WriteLine($"[HeartbeatService] Including {results.Count} command results in heartbeat");
            }

            return results.Count > 0 ? results : null;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[HeartbeatService] Failed to read command results: {ex.Message}");
            return null;
        }
    }

    private async void OnHeartbeatTick(object? state)
    {
        if (AppState.Instance.Phase != Phase.Connected)
            return;

        try
        {
            // Read command results from file if available
            var commandResults = ReadCommandResults();

            var eventsQueued = SyncService.Instance.PendingEventCount;
            var data = await APIClient.Instance.SendHeartbeatAsync(eventsQueued, commandResults);

            // Update config if provided
            if (data.ConfigUpdate != null)
            {
                if (data.ConfigUpdate.HeartbeatIntervalSeconds > 0)
                {
                    UpdateInterval(data.ConfigUpdate.HeartbeatIntervalSeconds);
                }

                SyncService.Instance.UpdateConfig(data.ConfigUpdate);
            }

            // Process server commands (API returns command type strings)
            if (data.Commands != null)
            {
                foreach (var commandType in data.Commands)
                {
                    ProcessCommand(commandType);
                }
            }

            OximyLogger.Log(EventCode.HB_FETCH_001, "Heartbeat sent");
            Debug.WriteLine("[HeartbeatService] Heartbeat sent successfully");

            // Periodic health snapshot (every ~5 minutes assuming 60s interval)
            _healthCheckCounter++;
            if (_healthCheckCounter % 5 == 0)
            {
                OximyLogger.Log(EventCode.SYS_HEALTH_001, "System health snapshot",
                    new Dictionary<string, object>
                    {
                        ["mitm_running"] = App.MitmService.IsRunning,
                        ["proxy_enabled"] = App.ProxyService.IsProxyEnabled,
                        ["sensor_enabled"] = RemoteStateService.Instance.SensorEnabled,
                        ["network_connected"] = App.NetworkMonitorService.IsConnected,
                        ["cert_installed"] = App.CertificateService.IsCAInstalled,
                        ["memory_mb"] = Process.GetCurrentProcess().WorkingSet64 / (1024 * 1024),
                        ["uptime_seconds"] = (long)(DateTime.UtcNow - Process.GetCurrentProcess().StartTime.ToUniversalTime()).TotalSeconds
                    });
            }
        }
        catch (ApiException ex)
        {
            OximyLogger.Log(EventCode.HB_FAIL_201, "Heartbeat send failed",
                new Dictionary<string, object> { ["error"] = ex.Message });
            Debug.WriteLine($"[HeartbeatService] Heartbeat failed: {ex.Message}");

            if (ex.IsUnauthorized)
            {
                // Auth failure is handled by APIClient
            }
        }
        catch (Exception ex)
        {
            OximyLogger.Log(EventCode.HB_FAIL_201, "Heartbeat error",
                new Dictionary<string, object> { ["error"] = ex.Message });
            Debug.WriteLine($"[HeartbeatService] Heartbeat error: {ex.Message}");
        }
    }

    private void ProcessCommand(string commandType)
    {
        Debug.WriteLine($"[HeartbeatService] Processing command: {commandType}");

        switch (commandType.ToLowerInvariant())
        {
            case "sync_now":
                OximyLogger.Log(EventCode.HB_CMD_002, "Command executed",
                    new Dictionary<string, object> { ["command"] = commandType });
                SyncRequested?.Invoke(this, EventArgs.Empty);
                break;

            case "restart_proxy":
                OximyLogger.Log(EventCode.HB_CMD_002, "Command executed",
                    new Dictionary<string, object> { ["command"] = commandType });
                RestartProxyRequested?.Invoke(this, EventArgs.Empty);
                break;

            case "disable_proxy":
                OximyLogger.Log(EventCode.HB_CMD_002, "Command executed",
                    new Dictionary<string, object> { ["command"] = commandType });
                DisableProxyRequested?.Invoke(this, EventArgs.Empty);
                break;

            case "logout":
                OximyLogger.Log(EventCode.HB_CMD_002, "Command executed",
                    new Dictionary<string, object> { ["command"] = commandType });
                LogoutRequested?.Invoke(this, EventArgs.Empty);
                break;

            default:
                OximyLogger.Log(EventCode.HB_FAIL_202, "Unknown command received",
                    new Dictionary<string, object> { ["command"] = commandType });
                Debug.WriteLine($"[HeartbeatService] Unknown command: {commandType}");
                break;
        }
    }

    private void OnAuthenticationFailed(object? sender, EventArgs e)
    {
        Debug.WriteLine("[HeartbeatService] Authentication failed, triggering logout");
        LogoutRequested?.Invoke(this, EventArgs.Empty);
    }

    private void OnWorkspaceNameUpdated(object? sender, string workspaceName)
    {
        AppState.Instance.WorkspaceName = workspaceName;

        // Persist so it survives app restarts (auth callback may not include workspace_name)
        var settings = OximyWindows.Properties.Settings.Default;
        settings.WorkspaceName = workspaceName;
        settings.Save();
    }

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        Stop();

        APIClient.Instance.AuthenticationFailed -= OnAuthenticationFailed;
        APIClient.Instance.WorkspaceNameUpdated -= OnWorkspaceNameUpdated;
    }
}
