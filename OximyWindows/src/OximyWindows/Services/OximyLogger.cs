using System.Diagnostics;
using System.IO;
using System.Text.Json;
using OximyWindows.Core;
using Sentry;

namespace OximyWindows.Services;

/// <summary>
/// Central structured logger — wraps SentryService + Console + JSONL file output.
/// Usage: OximyLogger.Log(EventCode.MITM_START_002, "mitmproxy listening", new() { ["port"] = 1030 });
/// </summary>
public static class OximyLogger
{
    /// <summary>
    /// Session ID for cross-component correlation.
    /// Generated once per app launch, passed to addon via OXIMY_SESSION_ID env var.
    /// </summary>
    public static string SessionId { get; } = Guid.NewGuid().ToString();

    private static readonly object _logLock = new();
    private static int _seq;
    private static FileStream? _fileStream;
    private static StreamWriter? _writer;
    private static string _logFilePath = "";
    private const long MaxLogFileSize = 50_000_000; // 50 MB
    private const int MaxRotatedFiles = 5;
    private static bool _initialized;

    // MARK: - Initialization

    /// <summary>
    /// Initialize the logger. Must be called after Constants.EnsureDirectoriesExist().
    /// </summary>
    public static void Initialize()
    {
        if (_initialized) return;

        _logFilePath = Path.Combine(Constants.LogsDir, "app.jsonl");

        try
        {
            Directory.CreateDirectory(Constants.LogsDir);
            OpenLogFile();
            _initialized = true;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] Failed to initialize: {ex.Message}");
        }
    }

    // MARK: - Public API

    /// <summary>
    /// Log a structured event to Console + JSONL + Sentry.
    /// </summary>
    public static void Log(
        EventCode code,
        string message,
        Dictionary<string, object>? data = null,
        (string type, string code, string message)? err = null)
    {
        var now = DateTime.UtcNow;

        // Console output (human-readable)
        PrintConsole(code, message, data, now);

        // JSONL file output (AI-parseable) — seq assigned inside lock for ordering guarantee
        WriteJSONL(code, message, data, err, now);

        // Sentry output (dashboards + alerts)
        SendToSentry(code, message, data, err);
    }

    /// <summary>
    /// Update a Sentry scope tag.
    /// </summary>
    public static void SetTag(string key, string value)
    {
        if (!SentryService.IsInitialized) return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag(key, value);
        });
    }

    /// <summary>
    /// Flush and close the log file handle. Call before app exit.
    /// </summary>
    public static void Close()
    {
        lock (_logLock)
        {
            try
            {
                _writer?.Flush();
                _writer?.Close();
                _writer?.Dispose();
                _writer = null;

                _fileStream?.Dispose();
                _fileStream = null;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[OximyLogger] Close error: {ex.Message}");
            }
        }
    }

    // MARK: - Console Output

    private static void PrintConsole(
        EventCode code, string message, Dictionary<string, object>? data, DateTime timestamp)
    {
        var levelTag = code.GetLevel() switch
        {
            LogLevel.Debug => "[DEBUG]",
            LogLevel.Info => "[INFO] ",
            LogLevel.Warning => "[WARN] ",
            LogLevel.Error => "[ERROR]",
            LogLevel.Fatal => "[FATAL]",
            _ => "[INFO] "
        };

        var line = $"{levelTag} {code.GetCode()} {message}";

        if (data is { Count: > 0 })
        {
            var pairs = data
                .OrderBy(kvp => kvp.Key)
                .Select(kvp => $"{kvp.Key}={kvp.Value}");
            line += " | " + string.Join(" ", pairs);
        }

        Debug.WriteLine($"[Oximy] {line}");
    }

    // MARK: - JSONL File Output

    private static void WriteJSONL(
        EventCode code,
        string message,
        Dictionary<string, object>? data,
        (string type, string code, string message)? err,
        DateTime timestamp)
    {
        if (!_initialized) return;

        try
        {
            // Build entry outside lock (minimize lock hold time)
            var ctx = new Dictionary<string, object>
            {
                ["component"] = "dotnet",
                ["session_id"] = SessionId
            };

            var deviceId = AppState.Instance.DeviceId;
            if (!string.IsNullOrEmpty(deviceId))
                ctx["device_id"] = deviceId;

            var workspaceId = AppState.Instance.WorkspaceId;
            if (!string.IsNullOrEmpty(workspaceId))
                ctx["workspace_id"] = workspaceId;

            var workspaceName = AppState.Instance.WorkspaceName;
            if (!string.IsNullOrEmpty(workspaceName))
                ctx["workspace_name"] = workspaceName;

            var entry = new Dictionary<string, object>
            {
                ["v"] = 1,
                // seq assigned below under lock
                ["ts"] = timestamp.ToString("O"),
                ["code"] = code.GetCode(),
                ["level"] = code.GetLevel().ToString().ToLowerInvariant(),
                ["svc"] = code.GetService(),
                ["op"] = code.GetOperation(),
                ["msg"] = message,
                ["action"] = code.GetAction().GetActionString(),
                ["ctx"] = ctx
            };

            if (data is { Count: > 0 })
                entry["data"] = data;

            if (err.HasValue)
            {
                entry["err"] = new Dictionary<string, object>
                {
                    ["type"] = err.Value.type,
                    ["code"] = err.Value.code,
                    ["message"] = err.Value.message
                };
            }

            lock (_logLock)
            {
                // Assign seq under same lock as write to guarantee ordering
                _seq++;
                entry["seq"] = _seq;

                var jsonLine = JsonSerializer.Serialize(entry, _jsonOptions);
                RotateIfNeeded();
                _writer?.WriteLine(jsonLine);
                _writer?.Flush();
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] JSONL write error: {ex.Message}");
        }
    }

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = false
    };

    // MARK: - Sentry Output

    private static void SendToSentry(
        EventCode code,
        string message,
        Dictionary<string, object>? data,
        (string type, string code, string message)? err)
    {
        if (!SentryService.IsInitialized) return;

        try
        {
            var sentryLevel = code.GetLevel() switch
            {
                LogLevel.Debug => SentryLevel.Debug,
                LogLevel.Info => SentryLevel.Info,
                LogLevel.Warning => SentryLevel.Warning,
                LogLevel.Error => SentryLevel.Error,
                LogLevel.Fatal => SentryLevel.Fatal,
                _ => SentryLevel.Info
            };

            var breadcrumbLevel = code.GetLevel() switch
            {
                LogLevel.Debug => BreadcrumbLevel.Debug,
                LogLevel.Info => BreadcrumbLevel.Info,
                LogLevel.Warning => BreadcrumbLevel.Warning,
                LogLevel.Error => BreadcrumbLevel.Error,
                LogLevel.Fatal => BreadcrumbLevel.Critical,
                _ => BreadcrumbLevel.Info
            };

            // Always add breadcrumb for info+
            if (code.GetLevel() >= LogLevel.Info)
            {
                var breadcrumbData = data?.ToDictionary(
                    kvp => kvp.Key,
                    kvp => kvp.Value?.ToString() ?? "");

                SentrySdk.AddBreadcrumb(
                    message: $"[{code.GetCode()}] {message}",
                    category: code.GetService(),
                    type: code.GetLevel() >= LogLevel.Warning ? "error" : "info",
                    data: breadcrumbData,
                    level: breadcrumbLevel);
            }

            // Capture Sentry event for warning+
            if (code.GetLevel() >= LogLevel.Warning)
            {
                SentrySdk.CaptureMessage($"[{code.GetCode()}] {message}", scope =>
                {
                    scope.Level = sentryLevel;
                    scope.SetTag("event_code", code.GetCode());
                    scope.SetTag("service", code.GetService());
                    scope.SetTag("operation", code.GetOperation());
                    scope.SetTag("action_category", code.GetAction().GetActionString());

                    if (err.HasValue)
                        scope.SetTag("error_code", err.Value.code);

                    if (data is { Count: > 0 })
                    {
                        foreach (var kvp in data)
                        {
                            scope.SetExtra(kvp.Key, kvp.Value);
                        }
                    }
                });
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] Sentry error: {ex.Message}");
        }
    }

    // MARK: - File Management

    private static void OpenLogFile()
    {
        try
        {
            _fileStream = new FileStream(
                _logFilePath,
                FileMode.Append,
                FileAccess.Write,
                FileShare.Read);
            _writer = new StreamWriter(_fileStream) { AutoFlush = false };
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] Failed to open log file: {ex.Message}");
        }
    }

    /// <summary>
    /// Rotate if file exceeds max size. Must be called under _logLock.
    /// </summary>
    private static void RotateIfNeeded()
    {
        try
        {
            if (_fileStream == null) return;

            if (_fileStream.Length <= MaxLogFileSize) return;

            // Close current file
            _writer?.Dispose();
            _writer = null;
            _fileStream?.Dispose();
            _fileStream = null;

            // Move current to temp first — protects data if subsequent moves fail
            var tempPath = Path.Combine(Constants.LogsDir, "app.rotating.jsonl");
            File.Move(_logFilePath, tempPath, overwrite: true);

            // Delete the oldest rotated file
            var oldest = Path.Combine(Constants.LogsDir, $"app.{MaxRotatedFiles}.jsonl");
            if (File.Exists(oldest))
                File.Delete(oldest);

            // Shift rotated files: app.4.jsonl -> app.5.jsonl, ..., app.1.jsonl -> app.2.jsonl
            for (int i = MaxRotatedFiles - 1; i >= 1; i--)
            {
                var src = Path.Combine(Constants.LogsDir, $"app.{i}.jsonl");
                var dst = Path.Combine(Constants.LogsDir, $"app.{i + 1}.jsonl");

                if (File.Exists(src))
                    File.Move(src, dst);
            }

            // Temp -> app.1.jsonl
            File.Move(tempPath, Path.Combine(Constants.LogsDir, "app.1.jsonl"), overwrite: true);

            // Reopen
            OpenLogFile();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] Rotation error: {ex.Message}");
            // Try to reopen the file even if rotation failed
            try { OpenLogFile(); } catch { /* best effort */ }
        }
    }
}
