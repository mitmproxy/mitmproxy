using System.Text.Json;
using System.Text.Json.Serialization;

namespace OximyWindows.Models;

#region Device Registration

/// <summary>
/// Request payload for device registration.
/// </summary>
public class DeviceRegistrationRequest
{
    [JsonPropertyName("hostname")]
    public required string Hostname { get; set; }

    [JsonPropertyName("displayName")]
    public string? DisplayName { get; set; }

    [JsonPropertyName("os")]
    public string Os { get; set; } = "windows";

    [JsonPropertyName("osVersion")]
    public required string OsVersion { get; set; }

    [JsonPropertyName("sensorVersion")]
    public required string SensorVersion { get; set; }

    [JsonPropertyName("hardwareId")]
    public required string HardwareId { get; set; }

    [JsonPropertyName("permissions")]
    public DevicePermissions Permissions { get; set; } = new();
}

/// <summary>
/// Device permissions status.
/// </summary>
public class DevicePermissions
{
    [JsonPropertyName("networkCapture")]
    public bool NetworkCapture { get; set; } = true;

    [JsonPropertyName("systemExtension")]
    public bool SystemExtension { get; set; } = false;

    [JsonPropertyName("fullDiskAccess")]
    public bool FullDiskAccess { get; set; } = false;
}

/// <summary>
/// Response wrapper from device registration API.
/// </summary>
public class DeviceRegistrationResponse
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("data")]
    public DeviceRegistrationData? Data { get; set; }

    [JsonPropertyName("error")]
    public ApiError? Error { get; set; }

    // Convenience accessors
    public string DeviceId => Data?.DeviceId ?? "";
    public string DeviceToken => Data?.DeviceToken ?? "";
    public string WorkspaceName => Data?.WorkspaceName ?? "";
    public string WorkspaceId => Data?.WorkspaceId ?? "";
    public DeviceConfig? Config => Data?.Config;
}

/// <summary>
/// Device registration data inside the response.
/// </summary>
public class DeviceRegistrationData
{
    [JsonPropertyName("deviceId")]
    public required string DeviceId { get; set; }

    [JsonPropertyName("deviceName")]
    public string? DeviceName { get; set; }

    [JsonPropertyName("deviceToken")]
    public required string DeviceToken { get; set; }

    [JsonPropertyName("workspaceName")]
    public string? WorkspaceName { get; set; }

    [JsonPropertyName("workspaceId")]
    public required string WorkspaceId { get; set; }

    [JsonPropertyName("config")]
    public DeviceConfig? Config { get; set; }
}

/// <summary>
/// Device configuration from server.
/// </summary>
public class DeviceConfig
{
    [JsonPropertyName("heartbeatIntervalSeconds")]
    public int HeartbeatIntervalSeconds { get; set; } = 60;

    [JsonPropertyName("eventBatchSize")]
    public int EventBatchSize { get; set; } = 100;

    [JsonPropertyName("eventFlushIntervalSeconds")]
    public int EventFlushIntervalSeconds { get; set; } = 5;

    [JsonPropertyName("apiEndpoint")]
    public string? ApiEndpoint { get; set; }
}

#endregion

#region Heartbeat

/// <summary>
/// Request payload for device heartbeat.
/// </summary>
public class HeartbeatRequest
{
    [JsonPropertyName("sensorVersion")]
    public required string SensorVersion { get; set; }

    [JsonPropertyName("uptimeSeconds")]
    public int UptimeSeconds { get; set; }

    [JsonPropertyName("permissions")]
    public DevicePermissions Permissions { get; set; } = new();

    [JsonPropertyName("metrics")]
    public DeviceMetrics Metrics { get; set; } = new();

    [JsonPropertyName("commandResults")]
    public Dictionary<string, CommandResult>? CommandResults { get; set; }
}

/// <summary>
/// Result of a command executed by the Python addon.
/// Read from ~/.oximy/command-results.json and included in next heartbeat.
/// </summary>
public class CommandResult
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("executedAt")]
    public string ExecutedAt { get; set; } = "";

    [JsonPropertyName("error")]
    public string? Error { get; set; }
}

/// <summary>
/// Device metrics for heartbeat.
/// </summary>
public class DeviceMetrics
{
    [JsonPropertyName("cpuPercent")]
    public double? CpuPercent { get; set; }

    [JsonPropertyName("memoryMb")]
    public int? MemoryMb { get; set; }

    [JsonPropertyName("eventsQueued")]
    public int EventsQueued { get; set; }
}

/// <summary>
/// Response from heartbeat.
/// </summary>
public class HeartbeatResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "ok";

    [JsonPropertyName("workspaceName")]
    public string? WorkspaceName { get; set; }

    [JsonPropertyName("config")]
    public DeviceConfig? Config { get; set; }

    [JsonPropertyName("commands")]
    public List<ServerCommand>? Commands { get; set; }
}

/// <summary>
/// Server command to execute.
/// </summary>
public class ServerCommand
{
    [JsonPropertyName("type")]
    public required string Type { get; set; }

    [JsonPropertyName("payload")]
    public JsonElement? Payload { get; set; }
}

#endregion

#region Events

/// <summary>
/// Request payload for event batch submission.
/// </summary>
public class EventBatchRequest
{
    [JsonPropertyName("events")]
    public required List<JsonElement> Events { get; set; }
}

/// <summary>
/// Response from event batch submission.
/// </summary>
public class EventBatchResponse
{
    [JsonPropertyName("received")]
    public int Received { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = "ok";
}

#endregion

#region Sync State

/// <summary>
/// Tracks sync progress across trace files.
/// </summary>
public class SyncState
{
    [JsonPropertyName("files")]
    public Dictionary<string, FileSyncState> Files { get; set; } = new();
}

/// <summary>
/// Sync state for a single trace file.
/// </summary>
public class FileSyncState
{
    [JsonPropertyName("lastSyncedLine")]
    public int LastSyncedLine { get; set; }

    [JsonPropertyName("lastSyncedEventId")]
    public string? LastSyncedEventId { get; set; }

    [JsonPropertyName("lastSyncTime")]
    public DateTime LastSyncTime { get; set; }
}

#endregion

#region Error Response

/// <summary>
/// API error response.
/// </summary>
public class ApiErrorResponse
{
    [JsonPropertyName("error")]
    public ApiError? Error { get; set; }

    // Some APIs return message at root level
    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("statusCode")]
    public int? StatusCode { get; set; }
}

/// <summary>
/// API error details.
/// </summary>
public class ApiError
{
    [JsonPropertyName("code")]
    public string? Code { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }
}

#endregion
