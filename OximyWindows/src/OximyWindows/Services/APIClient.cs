using System.Diagnostics;
using System.Management;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using OximyWindows.Core;
using OximyWindows.Models;

namespace OximyWindows.Services;

/// <summary>
/// API client for communicating with the Oximy backend.
/// Handles device registration, heartbeats, and event submission.
/// </summary>
public class APIClient
{
    private static APIClient? _instance;
    public static APIClient Instance => _instance ??= new APIClient();

    private readonly HttpClient _httpClient;
    private int _authRetryCount;
    private readonly JsonSerializerOptions _jsonOptions;

    // Cache hardware ID to avoid expensive WMI queries (100-500ms each)
    private static string? _cachedHardwareId;

    // CPU usage tracking - requires two snapshots to compute percentage
    private static DateTime _lastCpuCheckTime = DateTime.UtcNow;
    private static TimeSpan _lastCpuUsed = TimeSpan.Zero;
    private static double? _lastCpuPercent;

    public event EventHandler? AuthenticationFailed;
    public event EventHandler<string>? WorkspaceNameUpdated;

    private APIClient()
    {
        // Bypass system proxy for API calls - we don't want our own traffic
        // going through mitmproxy (causes loops and connection issues)
        var handler = new HttpClientHandler
        {
            UseProxy = false
        };

        _httpClient = new HttpClient(handler)
        {
            BaseAddress = new Uri(Constants.ApiBaseUrl),
            Timeout = TimeSpan.FromSeconds(Constants.ApiTimeoutSeconds)
        };

        _httpClient.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue("application/json"));
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd($"Oximy-Windows/{Constants.Version}");

        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            WriteIndented = false,
            DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
        };
    }

    /// <summary>
    /// Fetch device info (including workspace name) using a device token.
    /// Called after browser auth callback to get workspace info not in the callback URL.
    /// </summary>
    public async Task<DeviceInfoData> FetchDeviceInfoAsync(string token)
    {
        using var httpRequest = new HttpRequestMessage(HttpMethod.Get, "devices/me");
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.SendAsync(httpRequest);
        var content = await response.Content.ReadAsStringAsync();

        Debug.WriteLine($"[APIClient] FetchDeviceInfo response: {(int)response.StatusCode}");

        if (!response.IsSuccessStatusCode)
        {
            var error = ParseErrorFromContent(content, response);
            throw new ApiException(error, response.StatusCode);
        }

        var result = JsonSerializer.Deserialize<DeviceInfoResponse>(content, _jsonOptions);

        if (result?.Data == null)
            throw new ApiException("Invalid device info response", HttpStatusCode.InternalServerError);

        return result.Data;
    }

    /// <summary>
    /// Register device with the backend using enrollment code.
    /// </summary>
    public async Task<DeviceRegistrationResponse> RegisterDeviceAsync(string enrollmentCode)
    {
        var request = new DeviceRegistrationRequest
        {
            Hostname = Environment.MachineName,
            DisplayName = AppState.Instance.DeviceName,
            OsVersion = Environment.OSVersion.VersionString,
            SensorVersion = Constants.Version,
            HardwareId = GetHardwareId(),
            Permissions = new DevicePermissions
            {
                NetworkCapture = true,
                SystemExtension = false,
                FullDiskAccess = false
            }
        };

        var requestJson = JsonSerializer.Serialize(request, _jsonOptions);
        var fullUrl = $"{Constants.ApiBaseUrl}{Constants.DeviceRegisterEndpoint}";

        Debug.WriteLine($"[APIClient] === REGISTRATION REQUEST ===");
        Debug.WriteLine($"[APIClient] URL: {fullUrl}");
        Debug.WriteLine($"[APIClient] Enrollment Code: {enrollmentCode}");
        Debug.WriteLine($"[APIClient] Request Body: {requestJson}");

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, Constants.DeviceRegisterEndpoint);
        httpRequest.Headers.Add("X-Enrollment-Token", enrollmentCode);
        httpRequest.Content = new StringContent(requestJson, Encoding.UTF8, "application/json");

        try
        {
            var response = await _httpClient.SendAsync(httpRequest);
            var responseContent = await response.Content.ReadAsStringAsync();

            Debug.WriteLine($"[APIClient] === REGISTRATION RESPONSE ===");
            Debug.WriteLine($"[APIClient] Status: {(int)response.StatusCode} {response.StatusCode}");
            Debug.WriteLine($"[APIClient] Response Body: {responseContent}");

            if (!response.IsSuccessStatusCode)
            {
                var error = ParseErrorFromContent(responseContent, response);
                Debug.WriteLine($"[APIClient] Parsed Error: {error}");
                throw new ApiException(error, response.StatusCode);
            }

            var result = JsonSerializer.Deserialize<DeviceRegistrationResponse>(responseContent, _jsonOptions);

            if (result == null)
                throw new ApiException("Invalid response from server", HttpStatusCode.InternalServerError);

            if (!result.Success || result.Data == null)
            {
                var errorMsg = result.Error?.Message ?? "Registration failed";
                Debug.WriteLine($"[APIClient] Registration failed: {errorMsg}");
                throw new ApiException(errorMsg, response.StatusCode);
            }

            Debug.WriteLine($"[APIClient] Registration successful! DeviceId: {result.DeviceId}");

            // Reset retry count on successful registration
            _authRetryCount = 0;

            return result;
        }
        catch (HttpRequestException ex)
        {
            Debug.WriteLine($"[APIClient] Network error: {ex.Message}");
            throw new ApiException($"Network error: {ex.Message}", 0);
        }
        catch (TaskCanceledException ex)
        {
            Debug.WriteLine($"[APIClient] Request timeout: {ex.Message}");
            throw new ApiException("Request timed out", 0);
        }
    }

    /// <summary>
    /// Send heartbeat to the backend.
    /// Returns the unwrapped HeartbeatData from the response envelope.
    /// </summary>
    public async Task<HeartbeatData> SendHeartbeatAsync(int eventsQueued, Dictionary<string, CommandResult>? commandResults = null)
    {
        var deviceToken = AppState.Instance.DeviceToken;
        if (string.IsNullOrEmpty(deviceToken))
            throw new ApiException("No device token", HttpStatusCode.Unauthorized);

        var request = new HeartbeatRequest
        {
            SensorVersion = Constants.Version,
            UptimeSeconds = GetUptimeSeconds(),
            Permissions = new DevicePermissions
            {
                NetworkCapture = true,
                SystemExtension = false,
                FullDiskAccess = false
            },
            Metrics = new DeviceMetrics
            {
                CpuPercent = GetCpuUsage(),
                MemoryMb = GetMemoryUsageMb(),
                EventsQueued = eventsQueued
            },
            CommandResults = commandResults
        };

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, Constants.DeviceHeartbeatEndpoint);
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", deviceToken);
        httpRequest.Content = new StringContent(
            JsonSerializer.Serialize(request, _jsonOptions),
            Encoding.UTF8,
            "application/json");

        var response = await _httpClient.SendAsync(httpRequest);

        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            await HandleUnauthorizedAsync();
            throw new ApiException("Unauthorized", HttpStatusCode.Unauthorized);
        }

        if (!response.IsSuccessStatusCode)
        {
            var error = await ParseErrorAsync(response);
            throw new ApiException(error, response.StatusCode);
        }

        // Reset retry count on success
        _authRetryCount = 0;

        var content = await response.Content.ReadAsStringAsync();
        var envelope = JsonSerializer.Deserialize<HeartbeatResponse>(content, _jsonOptions);
        var data = envelope?.Data ?? new HeartbeatData();

        // Update workspace name if server provides a different one
        if (!string.IsNullOrEmpty(data.WorkspaceName) && data.WorkspaceName != AppState.Instance.WorkspaceName)
        {
            WorkspaceNameUpdated?.Invoke(this, data.WorkspaceName);
        }

        return data;
    }

    /// <summary>
    /// Fetch sensor config directly from the API.
    /// Used as fallback when the Python addon is not running or stale.
    /// </summary>
    public async Task<SensorConfigData?> FetchSensorConfigAsync()
    {
        var deviceToken = AppState.Instance.DeviceToken;
        if (string.IsNullOrEmpty(deviceToken))
            return null;

        using var httpRequest = new HttpRequestMessage(HttpMethod.Get, Constants.SensorConfigEndpoint);
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", deviceToken);

        var response = await _httpClient.SendAsync(httpRequest);
        if (!response.IsSuccessStatusCode)
            return null;

        var content = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<SensorConfigResponse>(content, _jsonOptions);
        return result?.Data;
    }

    /// <summary>
    /// Post command execution results to the API for immediate feedback.
    /// Called when the C# app processes sensor-config commands directly (addon dead).
    /// Best-effort — failures are logged but don't affect app operation.
    /// </summary>
    public async Task PostCommandResultsAsync(Dictionary<string, CommandResult> results)
    {
        var deviceToken = AppState.Instance.DeviceToken;
        if (string.IsNullOrEmpty(deviceToken))
            return;

        try
        {
            var payload = new { commandResults = results };
            using var httpRequest = new HttpRequestMessage(HttpMethod.Post, Constants.CommandResultsEndpoint);
            httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", deviceToken);
            httpRequest.Content = new StringContent(
                JsonSerializer.Serialize(payload, _jsonOptions),
                Encoding.UTF8,
                "application/json");

            var response = await _httpClient.SendAsync(httpRequest);
            Debug.WriteLine($"[APIClient] Command results POST: {(int)response.StatusCode} ({string.Join(", ", results.Keys)})");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[APIClient] Failed to POST command results: {ex.Message}");
        }
    }

    /// <summary>
    /// Submit a batch of events to the backend.
    /// </summary>
    public async Task<EventBatchResponse> SubmitEventsAsync(List<JsonElement> events)
    {
        var deviceToken = AppState.Instance.DeviceToken;
        if (string.IsNullOrEmpty(deviceToken))
            throw new ApiException("No device token", HttpStatusCode.Unauthorized);

        var request = new EventBatchRequest { Events = events };
        var requestJson = JsonSerializer.Serialize(request, _jsonOptions);

        Debug.WriteLine($"[APIClient] === EVENTS REQUEST ===");
        Debug.WriteLine($"[APIClient] Events count: {events.Count}");
        Debug.WriteLine($"[APIClient] Request body preview: {requestJson.Substring(0, Math.Min(500, requestJson.Length))}...");

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, Constants.DeviceEventsEndpoint);
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", deviceToken);
        httpRequest.Content = new StringContent(requestJson, Encoding.UTF8, "application/json");

        var response = await _httpClient.SendAsync(httpRequest);
        var responseContent = await response.Content.ReadAsStringAsync();

        Debug.WriteLine($"[APIClient] === EVENTS RESPONSE ===");
        Debug.WriteLine($"[APIClient] Status: {(int)response.StatusCode} {response.StatusCode}");
        Debug.WriteLine($"[APIClient] Response: {responseContent}");

        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            await HandleUnauthorizedAsync();
            throw new ApiException("Unauthorized", HttpStatusCode.Unauthorized);
        }

        if (!response.IsSuccessStatusCode)
        {
            var error = ParseErrorFromContent(responseContent, response);
            throw new ApiException(error, response.StatusCode);
        }

        // Reset retry count on success
        _authRetryCount = 0;

        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<EventBatchResponse>(content, _jsonOptions)
            ?? new EventBatchResponse();
    }

    /// <summary>
    /// Handle unauthorized response with retry logic.
    /// </summary>
    private async Task HandleUnauthorizedAsync()
    {
        _authRetryCount++;
        Debug.WriteLine($"[APIClient] Auth failure {_authRetryCount}/{Constants.MaxAuthRetries}");

        OximyLogger.Log(EventCode.AUTH_FAIL_201, "API request failed",
            new Dictionary<string, object> { ["method"] = "API", ["path"] = "unauthorized", ["error"] = $"Auth failure {_authRetryCount}/{Constants.MaxAuthRetries}" });

        if (_authRetryCount >= Constants.MaxAuthRetries)
        {
            OximyLogger.Log(EventCode.AUTH_FAIL_301, "Max auth retries exceeded",
                new Dictionary<string, object> { ["retries"] = _authRetryCount });
            Debug.WriteLine("[APIClient] Max auth retries exceeded, triggering logout");
            _authRetryCount = 0;
            AuthenticationFailed?.Invoke(this, EventArgs.Empty);
        }
        else
        {
            // Exponential backoff
            var delay = (int)Math.Pow(2, _authRetryCount) * 1000;
            await Task.Delay(delay);
        }
    }

    /// <summary>
    /// Parse error response from API.
    /// </summary>
    private static async Task<string> ParseErrorAsync(HttpResponseMessage response)
    {
        try
        {
            var content = await response.Content.ReadAsStringAsync();
            return ParseErrorFromContent(content, response);
        }
        catch
        {
            return $"HTTP {(int)response.StatusCode}: {response.ReasonPhrase}";
        }
    }

    /// <summary>
    /// Parse error from already-read content.
    /// </summary>
    private static string ParseErrorFromContent(string content, HttpResponseMessage response)
    {
        try
        {
            var error = JsonSerializer.Deserialize<ApiErrorResponse>(content);
            return error?.Error?.Message ?? error?.Message ?? $"HTTP {(int)response.StatusCode}: {response.ReasonPhrase}";
        }
        catch
        {
            return $"HTTP {(int)response.StatusCode}: {response.ReasonPhrase}";
        }
    }

    /// <summary>
    /// Get hardware ID using WMI. Result is cached to avoid expensive repeated queries.
    /// </summary>
    public static string GetHardwareId()
    {
        // Return cached value if available
        if (_cachedHardwareId != null)
            return _cachedHardwareId;

        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT UUID FROM Win32_ComputerSystemProduct");
            foreach (var obj in searcher.Get())
            {
                var uuid = obj["UUID"]?.ToString();
                if (!string.IsNullOrEmpty(uuid) && uuid != "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")
                {
                    _cachedHardwareId = uuid;
                    return uuid;
                }
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[APIClient] Failed to get hardware ID: {ex.Message}");
        }

        // Fallback to machine name hash
        _cachedHardwareId = Convert.ToBase64String(
            System.Security.Cryptography.SHA256.HashData(
                Encoding.UTF8.GetBytes(Environment.MachineName)));
        return _cachedHardwareId;
    }

    /// <summary>
    /// Get system uptime in seconds.
    /// </summary>
    private static int GetUptimeSeconds()
    {
        return (int)(Environment.TickCount64 / 1000);
    }

    /// <summary>
    /// Get current CPU usage percentage (0-100) by comparing two snapshots.
    /// Returns the process CPU usage as a percentage of total available CPU.
    /// </summary>
    private static double? GetCpuUsage()
    {
        try
        {
            using var process = Process.GetCurrentProcess();
            var now = DateTime.UtcNow;
            var currentCpuUsed = process.TotalProcessorTime;

            var elapsed = (now - _lastCpuCheckTime).TotalMilliseconds;
            if (elapsed < 100) // Too soon for a meaningful measurement
                return _lastCpuPercent;

            var cpuDelta = (currentCpuUsed - _lastCpuUsed).TotalMilliseconds;
            var cpuPercent = cpuDelta / (elapsed * Environment.ProcessorCount) * 100.0;

            // Clamp to 0-100 range
            cpuPercent = Math.Max(0, Math.Min(100, cpuPercent));

            // Update snapshots
            _lastCpuCheckTime = now;
            _lastCpuUsed = currentCpuUsed;
            _lastCpuPercent = Math.Round(cpuPercent, 1);

            return _lastCpuPercent;
        }
        catch
        {
            return null;
        }
    }

    /// <summary>
    /// Get current memory usage in MB.
    /// </summary>
    private static int? GetMemoryUsageMb()
    {
        try
        {
            using var process = Process.GetCurrentProcess();
            return (int)(process.WorkingSet64 / (1024 * 1024));
        }
        catch
        {
            return null;
        }
    }
}

/// <summary>
/// Exception for API errors.
/// </summary>
public class ApiException : Exception
{
    public HttpStatusCode StatusCode { get; }

    public ApiException(string message, HttpStatusCode statusCode) : base(message)
    {
        StatusCode = statusCode;
    }

    public bool IsNetworkError => StatusCode == 0;
    public bool IsUnauthorized => StatusCode == HttpStatusCode.Unauthorized;
    public bool IsNotFound => StatusCode == HttpStatusCode.NotFound;
    public bool IsConflict => StatusCode == HttpStatusCode.Conflict;
    public bool IsRateLimited => StatusCode == HttpStatusCode.TooManyRequests;
}
