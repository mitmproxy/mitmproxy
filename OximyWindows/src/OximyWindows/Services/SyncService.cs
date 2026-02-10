using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text.Json;
using OximyWindows.Core;
using OximyWindows.Models;

namespace OximyWindows.Services;

/// <summary>
/// Sync status enum.
/// </summary>
public enum SyncStatus
{
    Idle,
    Syncing,
    Synced,
    Offline,
    Error
}

/// <summary>
/// Service for syncing captured events to the backend.
/// Handles offline queueing, batch uploads, and state persistence.
/// </summary>
public class SyncService : INotifyPropertyChanged, IDisposable
{
    private static SyncService? _instance;
    public static SyncService Instance => _instance ??= new SyncService();

    private Timer? _syncTimer;
    private int _batchSize;
    private int _flushIntervalMs;
    private SyncState _syncState;
    private readonly object _lock = new();
    private bool _disposed;
    private int _consecutiveFailures;
    private DateTime _lastSyncTime;

    private SyncStatus _status = SyncStatus.Idle;
    public SyncStatus Status
    {
        get => _status;
        private set => SetProperty(ref _status, value);
    }

    private int _pendingEventCount;
    public int PendingEventCount
    {
        get => _pendingEventCount;
        private set => SetProperty(ref _pendingEventCount, value);
    }

    private string? _lastError;
    public string? LastError
    {
        get => _lastError;
        private set => SetProperty(ref _lastError, value);
    }

    public DateTime LastSyncTime => _lastSyncTime;

    public event PropertyChangedEventHandler? PropertyChanged;

    private SyncService()
    {
        _batchSize = Constants.DefaultEventBatchSize;
        _flushIntervalMs = Constants.DefaultEventFlushIntervalSeconds * 1000;
        _syncState = LoadSyncState();

        // Subscribe to heartbeat events for immediate sync
        HeartbeatService.Instance.SyncRequested += OnSyncRequested;
    }

    /// <summary>
    /// Start the sync timer.
    /// </summary>
    public void Start()
    {
        lock (_lock)
        {
            if (_syncTimer != null)
                return;

            Debug.WriteLine($"[SyncService] Starting with interval {_flushIntervalMs}ms, batch size {_batchSize}");

            _syncTimer = new Timer(
                OnSyncTick,
                null,
                TimeSpan.FromSeconds(2), // Initial delay
                TimeSpan.FromMilliseconds(_flushIntervalMs));

            // Initial count - run on background thread to avoid blocking
            _ = Task.Run(() => UpdatePendingCountAsync());
        }
    }

    /// <summary>
    /// Stop the sync timer.
    /// </summary>
    public void Stop()
    {
        lock (_lock)
        {
            _syncTimer?.Dispose();
            _syncTimer = null;
            Debug.WriteLine("[SyncService] Stopped");
        }
    }

    /// <summary>
    /// Update configuration from server.
    /// </summary>
    public void UpdateConfig(DeviceConfig config)
    {
        lock (_lock)
        {
            if (config.EventBatchSize > 0)
                _batchSize = config.EventBatchSize;

            if (config.EventFlushIntervalSeconds > 0)
            {
                _flushIntervalMs = config.EventFlushIntervalSeconds * 1000;

                if (_syncTimer != null)
                {
                    _syncTimer.Change(
                        TimeSpan.FromMilliseconds(_flushIntervalMs),
                        TimeSpan.FromMilliseconds(_flushIntervalMs));
                }
            }

            Debug.WriteLine($"[SyncService] Config updated: batch={_batchSize}, interval={_flushIntervalMs}ms");
        }
    }

    /// <summary>
    /// Trigger an immediate sync by writing a force-sync trigger file
    /// that the Python addon watches, then perform sync.
    /// </summary>
    public async Task SyncNowAsync()
    {
        WriteForceSyncTrigger();
        await PerformSyncAsync();
    }

    /// <summary>
    /// Flush all pending events synchronously (for app shutdown).
    /// Writes a force-sync trigger file so the Python addon also flushes immediately.
    /// </summary>
    public void FlushSync(int timeoutMs = 5000)
    {
        Debug.WriteLine("[SyncService] Flushing pending events synchronously...");

        // Write force-sync trigger file for the Python addon
        WriteForceSyncTrigger();

        try
        {
            var cts = new CancellationTokenSource(timeoutMs);
            var task = PerformSyncAsync(forceAll: true);
            task.Wait(cts.Token);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Flush failed: {ex.Message}");
        }
    }

    /// <summary>
    /// Write the force-sync trigger file that the Python addon watches.
    /// The addon reads this file and immediately uploads pending events.
    /// </summary>
    private static void WriteForceSyncTrigger()
    {
        try
        {
            File.WriteAllText(Path.Combine(Constants.OximyDir, "force-sync"), "sync");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Failed to write force-sync trigger: {ex.Message}");
        }
    }

    /// <summary>
    /// Get total local storage size in bytes.
    /// </summary>
    public long GetStorageSizeBytes()
    {
        try
        {
            if (!Directory.Exists(Constants.TracesDir))
                return 0;

            return Directory.GetFiles(Constants.TracesDir, "*.jsonl")
                .Sum(f => new FileInfo(f).Length);
        }
        catch
        {
            return 0;
        }
    }

    /// <summary>
    /// Get human-readable storage size.
    /// </summary>
    public string GetStorageSizeFormatted()
    {
        var bytes = GetStorageSizeBytes();
        string[] sizes = ["B", "KB", "MB", "GB"];
        int order = 0;
        double size = bytes;

        while (size >= 1024 && order < sizes.Length - 1)
        {
            order++;
            size /= 1024;
        }

        return $"{size:0.##} {sizes[order]}";
    }

    /// <summary>
    /// Clear all local trace data.
    /// </summary>
    public void ClearLocalData()
    {
        try
        {
            if (Directory.Exists(Constants.TracesDir))
            {
                foreach (var file in Directory.GetFiles(Constants.TracesDir, "*.jsonl"))
                {
                    File.Delete(file);
                }
            }

            _syncState = new SyncState();
            SaveSyncState();
            _ = Task.Run(() => UpdatePendingCountAsync());

            Debug.WriteLine("[SyncService] Local data cleared");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Failed to clear data: {ex.Message}");
        }
    }

    /// <summary>
    /// Open traces folder in Explorer.
    /// </summary>
    public void OpenTracesFolder()
    {
        try
        {
            Directory.CreateDirectory(Constants.TracesDir);
            Process.Start("explorer.exe", Constants.TracesDir);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Failed to open folder: {ex.Message}");
        }
    }

    private void OnSyncRequested(object? sender, EventArgs e)
    {
        _ = SyncNowAsync();
    }

    private async void OnSyncTick(object? state)
    {
        if (AppState.Instance.Phase != Phase.Connected)
            return;

        await PerformSyncAsync();
    }

    private async Task PerformSyncAsync(bool forceAll = false)
    {
        if (Status == SyncStatus.Syncing)
            return;

        Status = SyncStatus.Syncing;
        _ = Task.Run(() => UpdatePendingCountAsync());

        try
        {
            var files = GetTraceFiles();
            var totalSynced = 0;

            foreach (var file in files)
            {
                var synced = await SyncFileAsync(file, forceAll);
                totalSynced += synced;

                if (!forceAll && totalSynced >= _batchSize)
                    break;
            }

            if (totalSynced > 0)
            {
                _lastSyncTime = DateTime.UtcNow;
                SaveSyncState();
                Debug.WriteLine($"[SyncService] Synced {totalSynced} events");
            }

            _consecutiveFailures = 0;
            LastError = null;
            Status = SyncStatus.Synced;
        }
        catch (ApiException ex) when (ex.IsNetworkError || ex.StatusCode == System.Net.HttpStatusCode.ServiceUnavailable)
        {
            _consecutiveFailures++;
            LastError = "Network unavailable";
            Status = SyncStatus.Offline;

            Debug.WriteLine($"[SyncService] Network error, retry in {GetRetryDelayMs()}ms");
        }
        catch (Exception ex)
        {
            _consecutiveFailures++;
            LastError = ex.Message;
            Status = SyncStatus.Error;

            Debug.WriteLine($"[SyncService] Sync error: {ex.Message}");
        }
        finally
        {
            // Run on background thread to avoid blocking UI
            _ = Task.Run(() => UpdatePendingCountAsync());
        }
    }

    private async Task<int> SyncFileAsync(string filePath, bool forceAll)
    {
        var fileName = Path.GetFileName(filePath);
        var state = _syncState.Files.GetValueOrDefault(fileName) ?? new FileSyncState();
        var events = new List<JsonElement>();
        var lineNumber = 0;

        try
        {
            using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var reader = new StreamReader(stream);

            string? line;
            while ((line = await reader.ReadLineAsync()) != null)
            {
                lineNumber++;

                // Skip already synced lines
                if (lineNumber <= state.LastSyncedLine)
                    continue;

                if (string.IsNullOrWhiteSpace(line))
                    continue;

                try
                {
                    var jsonDoc = JsonDocument.Parse(line);
                    events.Add(jsonDoc.RootElement.Clone());
                }
                catch (JsonException)
                {
                    Debug.WriteLine($"[SyncService] Invalid JSON on line {lineNumber}");
                }

                if (!forceAll && events.Count >= _batchSize)
                    break;
            }
        }
        catch (IOException ex)
        {
            Debug.WriteLine($"[SyncService] File read error: {ex.Message}");
            return 0;
        }

        if (events.Count == 0)
            return 0;

        // Submit batch to API
        var response = await APIClient.Instance.SubmitEventsAsync(events);

        // Update sync state
        state.LastSyncedLine = lineNumber;
        state.LastSyncTime = DateTime.UtcNow;
        _syncState.Files[fileName] = state;

        return response.Received;
    }

    private List<string> GetTraceFiles()
    {
        if (!Directory.Exists(Constants.TracesDir))
            return [];

        return Directory.GetFiles(Constants.TracesDir, "traces_*.jsonl")
            .OrderBy(f => f)
            .ToList();
    }

    /// <summary>
    /// Update pending count asynchronously on background thread.
    /// </summary>
    private async Task UpdatePendingCountAsync()
    {
        try
        {
            var count = 0;
            var files = GetTraceFiles();

            foreach (var file in files)
            {
                var fileName = Path.GetFileName(file);
                var state = _syncState.Files.GetValueOrDefault(fileName);
                var syncedLines = state?.LastSyncedLine ?? 0;
                var totalLines = await CountLinesAsync(file);

                count += Math.Max(0, totalLines - syncedLines);
            }

            PendingEventCount = count;
        }
        catch
        {
            PendingEventCount = 0;
        }
    }

    /// <summary>
    /// Count lines in a file asynchronously without blocking UI thread.
    /// </summary>
    private static async Task<int> CountLinesAsync(string filePath)
    {
        try
        {
            using var stream = new FileStream(
                filePath,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite,
                bufferSize: 65536,
                useAsync: true);

            var count = 0;
            var buffer = new byte[65536];
            int bytesRead;

            while ((bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length)) > 0)
            {
                for (int i = 0; i < bytesRead; i++)
                {
                    if (buffer[i] == '\n')
                        count++;
                }
            }

            return count;
        }
        catch
        {
            return 0;
        }
    }

    private int GetRetryDelayMs()
    {
        return Math.Min(60000, _flushIntervalMs * _consecutiveFailures);
    }

    private SyncState LoadSyncState()
    {
        try
        {
            if (File.Exists(Constants.SyncStatePath))
            {
                var json = File.ReadAllText(Constants.SyncStatePath);
                return JsonSerializer.Deserialize<SyncState>(json) ?? new SyncState();
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Failed to load sync state: {ex.Message}");
        }

        return new SyncState();
    }

    private void SaveSyncState()
    {
        try
        {
            var json = JsonSerializer.Serialize(_syncState, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(Constants.SyncStatePath, json);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SyncService] Failed to save sync state: {ex.Message}");
        }
    }

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        Stop();

        HeartbeatService.Instance.SyncRequested -= OnSyncRequested;
    }
}
