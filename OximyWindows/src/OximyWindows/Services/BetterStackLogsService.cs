using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using OximyWindows.Core;

namespace OximyWindows.Services;

public static class BetterStackLogsService
{
    private static bool _initialized;
    private static string? _sourceToken;
    private static string? _host;
    private static HttpClient? _httpClient;
    private static readonly ConcurrentQueue<Dictionary<string, object>> _buffer = new();
    private static Timer? _flushTimer;
    private static readonly object _flushLock = new();
    private const int MaxBufferSize = 20;
    private const int FlushIntervalMs = 5000;

    public static bool IsInitialized => _initialized;

    public static void Initialize()
    {
        if (_initialized) return;

        _sourceToken = Secrets.BetterStackLogsToken;
        _host = Secrets.BetterStackLogsHost;

        if (string.IsNullOrEmpty(_sourceToken) || string.IsNullOrEmpty(_host))
        {
            Debug.WriteLine("[BetterStackLogs] No token/host configured - logging disabled");
            return;
        }

        // Bypass proxy to avoid routing through mitmproxy
        var handler = new HttpClientHandler { UseProxy = false };
        _httpClient = new HttpClient(handler);
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {_sourceToken}");

        _flushTimer = new Timer(_ => Flush(), null, FlushIntervalMs, FlushIntervalMs);
        _initialized = true;
        Debug.WriteLine("[BetterStackLogs] Initialized successfully");
    }

    public static void Enqueue(Dictionary<string, object> entry)
    {
        if (!_initialized) return;

        _buffer.Enqueue(entry);

        if (_buffer.Count >= MaxBufferSize)
            Flush();
    }

    public static void Flush()
    {
        if (!_initialized || _buffer.IsEmpty) return;

        lock (_flushLock)
        {
            var entries = new List<Dictionary<string, object>>();
            while (_buffer.TryDequeue(out var entry))
                entries.Add(entry);

            if (entries.Count == 0) return;

            _ = SendBatchAsync(entries); // fire and forget
        }
    }

    private static async Task SendBatchAsync(List<Dictionary<string, object>> entries)
    {
        try
        {
            var json = JsonSerializer.Serialize(entries);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            await _httpClient!.PostAsync(_host, content);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[BetterStackLogs] Send error: {ex.Message}");
            // fail-open: silently swallow
        }
    }

    public static void Close()
    {
        if (!_initialized) return;

        try
        {
            _flushTimer?.Dispose();
            _flushTimer = null;
            Flush(); // send remaining
            _httpClient?.Dispose();
            _httpClient = null;
            _initialized = false;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[BetterStackLogs] Close error: {ex.Message}");
        }
    }
}
