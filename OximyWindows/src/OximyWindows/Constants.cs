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

    // Certificate configuration
    public const string CACommonName = "Oximy CA";
    public const string CAOrganization = "Oximy Inc";
    public const string CACountry = "US";
    public const int CAValidityDays = 3650; // 10 years

    // Directory paths
    public static string OximyDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".oximy");

    public static string TracesDir => Path.Combine(OximyDir, "traces");
    public static string LogsDir => Path.Combine(OximyDir, "logs");
    public static string CacheDir => Path.Combine(OximyDir, "cache");

    // Certificate file paths
    public static string CACertPath => Path.Combine(OximyDir, "mitmproxy-ca-cert.pem");
    public static string CAKeyPath => Path.Combine(OximyDir, "mitmproxy-ca.pem");

    // Python paths (relative to app directory)
    public static string PythonEmbedDir => Path.Combine(AppContext.BaseDirectory, "Resources", "python-embed");
    public static string PythonExePath => Path.Combine(PythonEmbedDir, "python.exe");
    public static string MitmdumpExePath => Path.Combine(PythonEmbedDir, "Scripts", "mitmdump.exe");
    public static string AddonDir => Path.Combine(AppContext.BaseDirectory, "Resources", "oximy-addon");
    public static string AddonPath => Path.Combine(AddonDir, "addon.py");

    // URLs
    public const string SignUpUrl = "https://oximy.com/signup";
    public const string HelpUrl = "https://oximy.com/help";
    public const string SupportEmail = "support@oximy.com";
    public const string TermsUrl = "https://oximy.com/terms";
    public const string PrivacyUrl = "https://oximy.com/privacy";
    public const string GitHubUrl = "https://github.com/oximy/oximy";
    public const string FeedbackUrl = "https://github.com/oximy/oximy/issues";

    // API URLs
    public const string ApiBaseUrl = "https://api.oximy.com";
    public const string OispBundleUrl = "https://oisp.dev/spec/v0.1/oisp-spec-bundle.json";

    // Proxy bypass list
    public const string ProxyBypassList = "localhost;127.0.0.1;<local>";

    // Settings keys
    public const string SettingsOnboardingComplete = "OnboardingComplete";
    public const string SettingsWorkspaceName = "WorkspaceName";
    public const string SettingsDeviceToken = "DeviceToken";
    public const string SettingsDeviceName = "DeviceName";

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
    /// Count events captured today.
    /// </summary>
    public static int CountTodayEvents()
    {
        var today = DateTime.UtcNow.Date;
        var pattern = $"events-{today:yyyy-MM-dd}-*.jsonl";

        try
        {
            var files = Directory.GetFiles(TracesDir, pattern);
            var count = 0;

            foreach (var file in files)
            {
                count += File.ReadLines(file).Count();
            }

            return count;
        }
        catch
        {
            return 0;
        }
    }
}
