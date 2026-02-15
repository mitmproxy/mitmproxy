using System.Diagnostics;
using System.IO;
using System.Text.Json;
using OximyWindows.Core;
using Sentry;

namespace OximyWindows.Services;

public static class OximyLogger
{
    public static string SessionId { get; } = Guid.NewGuid().ToString();
    public static bool IsSetupComplete { get; set; } = false;

    private static readonly object _logLock = new();
    private static int _seq;
    private static FileStream? _fileStream;
    private static StreamWriter? _writer;
    private static string _logFilePath = "";
    private const long MaxLogFileSize = 50_000_000; // 50 MB
    private const int MaxRotatedFiles = 5;
    private static bool _initialized;

    private static readonly Dictionary<string, (int count, DateTime windowStart)> _rateLimiter = new();
    private const int MaxEventsPerWindow = 10;
    private static readonly TimeSpan RateWindow = TimeSpan.FromSeconds(60);

    // Level mappings (shared across console and Sentry)
    private static readonly Dictionary<LogLevel, string> _levelTags = new()
    {
        [LogLevel.Debug] = "[DEBUG]",
        [LogLevel.Info] = "[INFO] ",
        [LogLevel.Warning] = "[WARN] ",
        [LogLevel.Error] = "[ERROR]",
        [LogLevel.Fatal] = "[FATAL]",
    };

    private static readonly Dictionary<LogLevel, SentryLevel> _sentryLevels = new()
    {
        [LogLevel.Debug] = SentryLevel.Debug,
        [LogLevel.Info] = SentryLevel.Info,
        [LogLevel.Warning] = SentryLevel.Warning,
        [LogLevel.Error] = SentryLevel.Error,
        [LogLevel.Fatal] = SentryLevel.Fatal,
    };

    private static readonly Dictionary<LogLevel, BreadcrumbLevel> _breadcrumbLevels = new()
    {
        [LogLevel.Debug] = BreadcrumbLevel.Debug,
        [LogLevel.Info] = BreadcrumbLevel.Info,
        [LogLevel.Warning] = BreadcrumbLevel.Warning,
        [LogLevel.Error] = BreadcrumbLevel.Error,
        [LogLevel.Fatal] = BreadcrumbLevel.Critical,
    };

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

    public static void Log(
        EventCode code,
        string message,
        Dictionary<string, object>? data = null,
        (string type, string code, string message)? err = null)
    {
        var now = DateTime.UtcNow;

        PrintConsole(code, message, data, now);
        WriteJSONL(code, message, data, err, now);
        SendToSentry(code, message, data, err);
        SendToBetterStackLogs(code, message, data, err, now);
    }

    public static void SetTag(string key, string value)
    {
        if (!SentryService.IsInitialized) return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag(key, value);
        });
    }

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

    private static void PrintConsole(
        EventCode code, string message, Dictionary<string, object>? data, DateTime timestamp)
    {
        var levelTag = _levelTags.GetValueOrDefault(code.GetLevel(), "[INFO] ");
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
            var ctx = new Dictionary<string, object>
            {
                ["component"] = "dotnet",
                ["session_id"] = SessionId
            };

            AddIfPresent(ctx, "device_id", AppState.Instance.DeviceId);
            AddIfPresent(ctx, "workspace_id", AppState.Instance.WorkspaceId);
            AddIfPresent(ctx, "workspace_name", AppState.Instance.WorkspaceName);

            var (service, operation) = code.GetServiceAndOperation();

            var entry = new Dictionary<string, object>
            {
                ["v"] = 1,
                ["ts"] = timestamp.ToString("O"),
                ["code"] = code.GetCode(),
                ["level"] = code.GetLevel().ToString().ToLowerInvariant(),
                ["svc"] = service,
                ["op"] = operation,
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

    private static void SendToSentry(
        EventCode code,
        string message,
        Dictionary<string, object>? data,
        (string type, string code, string message)? err)
    {
        if (!SentryService.IsInitialized) return;

        try
        {
            var level = code.GetLevel();
            if (level < LogLevel.Info) return;

            var sentryLevel = _sentryLevels.GetValueOrDefault(level, SentryLevel.Info);
            var breadcrumbLevel = _breadcrumbLevels.GetValueOrDefault(level, BreadcrumbLevel.Info);

            var breadcrumbData = data?.ToDictionary(
                kvp => kvp.Key,
                kvp => kvp.Value?.ToString() ?? "");

            SentrySdk.AddBreadcrumb(
                message: $"[{code.GetCode()}] {message}",
                category: code.GetService(),
                type: level >= LogLevel.Warning ? "error" : "info",
                data: breadcrumbData,
                level: breadcrumbLevel);

            // During setup, only suppress operational warnings (let .info lifecycle events through)
            if (!IsSetupComplete && level == LogLevel.Warning)
                return;

            if (ShouldSendSentryEvent(code))
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

    private static bool ShouldSendSentryEvent(EventCode code)
    {
        var key = code.GetCode();
        var now = DateTime.UtcNow;

        lock (_rateLimiter)
        {
            if (_rateLimiter.TryGetValue(key, out var entry))
            {
                if (now - entry.windowStart < RateWindow)
                {
                    if (entry.count >= MaxEventsPerWindow)
                        return false;

                    _rateLimiter[key] = (entry.count + 1, entry.windowStart);
                    return true;
                }
            }

            _rateLimiter[key] = (1, now);
            return true;
        }
    }

    private static void AddIfPresent(Dictionary<string, object> dict, string key, string? value)
    {
        if (!string.IsNullOrEmpty(value))
            dict[key] = value;
    }

    private static void SendToBetterStackLogs(
        EventCode code,
        string message,
        Dictionary<string, object>? data,
        (string type, string code, string message)? err,
        DateTime timestamp)
    {
        if (!BetterStackLogsService.IsInitialized) return;

        var level = code.GetLevel();
        if (level < LogLevel.Info) return;

        try
        {
            var (service, operation) = code.GetServiceAndOperation();

            var ctx = new Dictionary<string, object>
            {
                ["component"] = "dotnet",
                ["session_id"] = SessionId
            };

            AddIfPresent(ctx, "device_id", AppState.Instance.DeviceId);
            AddIfPresent(ctx, "workspace_id", AppState.Instance.WorkspaceId);
            AddIfPresent(ctx, "workspace_name", AppState.Instance.WorkspaceName);

            var entry = new Dictionary<string, object>
            {
                ["dt"] = timestamp.ToString("O"),
                ["v"] = 1,
                ["code"] = code.GetCode(),
                ["level"] = level.ToString().ToLowerInvariant(),
                ["svc"] = service,
                ["op"] = operation,
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

            BetterStackLogsService.Enqueue(entry);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] BetterStack error: {ex.Message}");
        }
    }

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

    private static void RotateIfNeeded()
    {
        try
        {
            if (_fileStream == null) return;

            if (_fileStream.Length <= MaxLogFileSize) return;

            _writer?.Dispose();
            _writer = null;
            _fileStream?.Dispose();
            _fileStream = null;

            var tempPath = Path.Combine(Constants.LogsDir, "app.rotating.jsonl");
            File.Move(_logFilePath, tempPath, overwrite: true);

            var oldest = Path.Combine(Constants.LogsDir, $"app.{MaxRotatedFiles}.jsonl");
            if (File.Exists(oldest))
                File.Delete(oldest);

            for (int i = MaxRotatedFiles - 1; i >= 1; i--)
            {
                var src = Path.Combine(Constants.LogsDir, $"app.{i}.jsonl");
                var dst = Path.Combine(Constants.LogsDir, $"app.{i + 1}.jsonl");

                if (File.Exists(src))
                    File.Move(src, dst);
            }

            File.Move(tempPath, Path.Combine(Constants.LogsDir, "app.1.jsonl"), overwrite: true);

            OpenLogFile();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[OximyLogger] Rotation error: {ex.Message}");
            try { OpenLogFile(); } catch { /* best effort */ }
        }
    }
}
