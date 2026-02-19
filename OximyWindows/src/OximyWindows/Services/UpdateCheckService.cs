using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
using OximyWindows.Core;

namespace OximyWindows.Services;

/// <summary>
/// Checks for app updates by fetching version.json from GitHub Releases.
/// Respects MDM-managed deployments by skipping the check entirely.
/// </summary>
public class UpdateCheckService
{
    private static UpdateCheckService? _instance;
    public static UpdateCheckService Instance => _instance ??= new UpdateCheckService();

    private const string VersionCheckUrl = "https://github.com/OximyHQ/sensor/releases/download/latest/version.json";

    private bool _hasChecked;

    public bool UpdateAvailable { get; private set; }
    public bool Unsupported { get; private set; }
    public string? LatestVersion { get; private set; }
    public string? DownloadUrl { get; private set; }

    public event EventHandler? UpdateStatusChanged;

    private UpdateCheckService() { }

    /// <summary>
    /// Check for updates once on app launch. Fails silently.
    /// </summary>
    public async Task CheckOnceAsync()
    {
        if (_hasChecked) return;
        _hasChecked = true;

        // Skip update checks for MDM-managed devices
        if (MDMConfigService.Instance.IsManagedDevice) return;

        try
        {
            await CheckAsync();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[UpdateCheck] Failed: {ex.Message}");
            // Fail silently — update check is best-effort
        }
    }

    private async Task CheckAsync()
    {
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        var response = await client.GetAsync(VersionCheckUrl);

        if (!response.IsSuccessStatusCode) return;

        var json = await response.Content.ReadAsStringAsync();
        var info = JsonSerializer.Deserialize<VersionInfo>(json);
        if (info == null) return;

        var currentVersion = Constants.Version;

        if (CompareVersions(currentVersion, info.MinSupported) < 0)
        {
            // Below minimum supported version
            LatestVersion = info.Latest;
            DownloadUrl = info.Download?.Windows;
            Unsupported = true;
            UpdateAvailable = true;
            UpdateStatusChanged?.Invoke(this, EventArgs.Empty);
        }
        else if (CompareVersions(currentVersion, info.Latest) < 0)
        {
            // Update available but not critical
            LatestVersion = info.Latest;
            DownloadUrl = info.Download?.Windows;
            UpdateAvailable = true;
            UpdateStatusChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    /// <summary>
    /// Semantic version comparison. Returns negative if a &lt; b, 0 if equal, positive if a &gt; b.
    /// </summary>
    private static int CompareVersions(string a, string b)
    {
        var aParts = a.Split('.').Select(s => int.TryParse(s, out var n) ? n : 0).ToArray();
        var bParts = b.Split('.').Select(s => int.TryParse(s, out var n) ? n : 0).ToArray();
        var maxLen = Math.Max(aParts.Length, bParts.Length);

        for (int i = 0; i < maxLen; i++)
        {
            var aVal = i < aParts.Length ? aParts[i] : 0;
            var bVal = i < bParts.Length ? bParts[i] : 0;
            if (aVal != bVal) return aVal.CompareTo(bVal);
        }
        return 0;
    }

    private class VersionInfo
    {
        [JsonPropertyName("latest")]
        public string Latest { get; set; } = "";

        [JsonPropertyName("min_supported")]
        public string MinSupported { get; set; } = "";

        [JsonPropertyName("download")]
        public DownloadInfo? Download { get; set; }
    }

    private class DownloadInfo
    {
        [JsonPropertyName("macos")]
        public string? Macos { get; set; }

        [JsonPropertyName("windows")]
        public string? Windows { get; set; }
    }
}
