using System.IO;

namespace OximyWindows;

/// <summary>
/// Application-wide constants and configuration.
/// </summary>
public static class Constants
{
    // Version
    public const string Version = "1.0.0";

    // Port configuration (1030 is the founding date)
    public const int PreferredPort = 1030;
    public const int PortSearchRange = 100;

    // Auto-restart configuration
    public const int MaxRestartAttempts = 3;

    // Certificate validity (mitmproxy defaults to 10 years for CA)
    public const int CAValidityDays = 3650; // 10 years - for reference only

    // Directory paths
    public static string OximyDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".oximy");

    // mitmproxy uses its own directory for certificates
    public static string MitmproxyDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".mitmproxy");

    public static string TracesDir => Path.Combine(OximyDir, "traces");
    public static string LogsDir => Path.Combine(OximyDir, "logs");
    public static string CacheDir => Path.Combine(OximyDir, "cache");
    public static string SyncStatePath => Path.Combine(OximyDir, "sync_state.json");

    // Certificate file paths - use oximy naming (matches CONF_BASENAME in mitmproxy/options.py)
    // mitmproxy auto-generates these when it starts with CN=oximy
    public static string CACertPath => Path.Combine(MitmproxyDir, "oximy-ca-cert.pem");
    public static string CAKeyPath => Path.Combine(MitmproxyDir, "oximy-ca.pem");

    // Python paths (relative to app directory)
    public static string PythonEmbedDir => Path.Combine(AppContext.BaseDirectory, "Resources", "python-embed");
    public static string PythonExePath => Path.Combine(PythonEmbedDir, "python.exe");
    public static string MitmdumpExePath => Path.Combine(PythonEmbedDir, "Scripts", "mitmdump.exe");
    public static string AddonDir => Path.Combine(AppContext.BaseDirectory, "Resources", "oximy-addon");
    public static string AddonPath => Path.Combine(AddonDir, "addon.py");

    // URLs (matching Mac app)
    public const string SignUpUrl = "https://staging.oximy.com";
    public const string HelpUrl = "https://docs.oximy.com";
    public const string SupportEmail = "support@oximy.com";
    public const string TermsUrl = "https://oximy.com/terms";
    public const string PrivacyUrl = "https://oximy.com/privacy";
    public const string GitHubUrl = "https://github.com/oximyhq/sensor";
    public const string FeedbackUrl = "https://github.com/oximyhq/sensor/issues";

    // API URLs (must end with trailing slash for proper URI resolution)
    public const string DefaultApiBaseUrl = "https://api.oximy.com/api/v1/";  // Production API
    public const string OispBundleUrl = "https://oisp.dev/spec/v0.1/oisp-spec-bundle.json";

    /// <summary>
    /// Dev config file path (~/.oximy/dev.json)
    /// </summary>
    public static string DevConfigPath => Path.Combine(OximyDir, "dev.json");

    /// <summary>
    /// Returns API base URL from dev config if available, otherwise default.
    /// Dev config JSON format: {"API_URL": "http://localhost:4000/api/v1/", "DEV_MODE": true}
    /// </summary>
    public static string ApiBaseUrl
    {
        get
        {
            // Check for OXIMY_DEV environment variable first
            var devEnv = Environment.GetEnvironmentVariable("OXIMY_DEV")?.ToLower();
            if (devEnv == "1" || devEnv == "true" || devEnv == "yes")
            {
                // Check for custom API URL in environment
                var apiUrl = Environment.GetEnvironmentVariable("OXIMY_API_URL");
                if (!string.IsNullOrEmpty(apiUrl))
                {
                    // Ensure trailing slash
                    return apiUrl.EndsWith("/") ? apiUrl : apiUrl + "/";
                }
            }

            // Check for local dev config file
            try
            {
                if (File.Exists(DevConfigPath))
                {
                    var json = File.ReadAllText(DevConfigPath);
                    var config = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(json);
                    if (config != null && config.TryGetValue("API_URL", out var apiUrlObj))
                    {
                        var apiUrl = apiUrlObj?.ToString();
                        if (!string.IsNullOrEmpty(apiUrl))
                        {
                            // Ensure trailing slash
                            return apiUrl.EndsWith("/") ? apiUrl : apiUrl + "/";
                        }
                    }
                }
            }
            catch
            {
                // Ignore config read errors, fall back to default
            }

            return DefaultApiBaseUrl;
        }
    }

    // API Endpoints (no leading slash - relative to BaseAddress)
    public const string DeviceRegisterEndpoint = "devices/register";
    public const string DeviceHeartbeatEndpoint = "devices/heartbeat";
    public const string DeviceEventsEndpoint = "devices/events";

    // Sync Configuration
    public const int DefaultHeartbeatIntervalSeconds = 60;
    public const int DefaultEventBatchSize = 100;
    public const int DefaultEventFlushIntervalSeconds = 5;
    public const int MaxAuthRetries = 5;
    public const int ApiTimeoutSeconds = 30;

    // Proxy bypass list
    public const string ProxyBypassList = "localhost;127.0.0.1;<local>";

    // Settings keys
    public const string SettingsOnboardingComplete = "OnboardingComplete";
    public const string SettingsWorkspaceName = "WorkspaceName";
    public const string SettingsDeviceToken = "DeviceToken";
    public const string SettingsDeviceName = "DeviceName";

    // Auth constants for browser-based enrollment
    public const string AuthStateKey = "authState";
    public const string AuthUrl = "https://staging.oximy.com/auth/enroll";

    // Remote state file path (written by Python addon)
    public static string RemoteStatePath => Path.Combine(OximyDir, "remote-state.json");

    /// <summary>
    /// Ensure all required directories exist.
    /// </summary>
    public static void EnsureDirectoriesExist()
    {
        Directory.CreateDirectory(OximyDir);
        Directory.CreateDirectory(TracesDir);
        Directory.CreateDirectory(LogsDir);
        Directory.CreateDirectory(CacheDir);
    }

    /// <summary>
    /// Get today's events file path.
    /// </summary>
    public static string GetTodayEventsFilePath()
    {
        var now = DateTime.UtcNow;
        var filename = $"events-{now:yyyy-MM-dd-HH}.jsonl";
        return Path.Combine(TracesDir, filename);
    }

    /// <summary>
    /// Count events captured today by counting newlines efficiently.
    /// Uses buffered reading instead of reading all lines into memory.
    /// </summary>
    public static int CountTodayEvents()
    {
        var today = DateTime.UtcNow.Date;
        var pattern = $"traces_{today:yyyy-MM-dd}.jsonl";

        try
        {
            if (!Directory.Exists(TracesDir))
                return 0;

            var files = Directory.GetFiles(TracesDir, pattern);
            var count = 0;

            foreach (var file in files)
            {
                count += CountLinesInFile(file);
            }

            return count;
        }
        catch
        {
            return 0;
        }
    }

    /// <summary>
    /// Efficiently count lines in a file using buffered reading.
    /// Much faster than File.ReadLines().Count() for large files.
    /// </summary>
    private static int CountLinesInFile(string filePath)
    {
        const int bufferSize = 65536; // 64KB buffer
        var buffer = new byte[bufferSize];
        var lineCount = 0;

        try
        {
            using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite, bufferSize);
            int bytesRead;

            while ((bytesRead = stream.Read(buffer, 0, bufferSize)) > 0)
            {
                for (int i = 0; i < bytesRead; i++)
                {
                    if (buffer[i] == '\n')
                        lineCount++;
                }
            }
        }
        catch
        {
            // File might be locked or deleted
        }

        return lineCount;
    }
}
