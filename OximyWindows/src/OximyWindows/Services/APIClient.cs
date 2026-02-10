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
            WriteIndented = false
        };
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
    /// </summary>
    public async Task<HeartbeatResponse> SendHeartbeatAsync(int eventsQueued, Dictionary<string, CommandResult>? commandResults = null)
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
        var result = JsonSerializer.Deserialize<HeartbeatResponse>(content, _jsonOptions);

        if (result?.WorkspaceName != null && result.WorkspaceName != AppState.Instance.WorkspaceName)
        {
            WorkspaceNameUpdated?.Invoke(this, result.WorkspaceName);
        }

        return result ?? new HeartbeatResponse();
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

        if (_authRetryCount >= Constants.MaxAuthRetries)
        {
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
    /// Get current CPU usage percentage.
    /// </summary>
    private static double? GetCpuUsage()
    {
        try
        {
            using var process = Process.GetCurrentProcess();
            return process.TotalProcessorTime.TotalMilliseconds / Environment.ProcessorCount / 10;
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
