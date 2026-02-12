using System.Diagnostics;
using System.Runtime.InteropServices;
using OximyWindows.Core;
using Sentry;

namespace OximyWindows.Services;

/// <summary>
/// Sentry integration for error tracking and performance monitoring.
/// Matches the Mac app's SentryService functionality.
/// </summary>
public static class SentryService
{
    private static bool _initialized;
    private static string? _anonymousDeviceId;

    /// <summary>
    /// Whether Sentry has been initialized. Used by OximyLogger to guard Sentry calls.
    /// </summary>
    public static bool IsInitialized => _initialized;

    /// <summary>
    /// Sentry DSN - should be set via environment variable or secrets file.
    /// </summary>
    private static string? SentryDsn =>
        Environment.GetEnvironmentVariable("SENTRY_DSN") ??
        Secrets.SentryDsn;

    /// <summary>
    /// Initialize Sentry SDK. Must be called before any other Sentry operations.
    /// </summary>
    public static void Initialize()
    {
        if (_initialized)
            return;

        var dsn = SentryDsn;
        if (string.IsNullOrEmpty(dsn))
        {
            Debug.WriteLine("[SentryService] No DSN configured, Sentry disabled");
            return;
        }

        try
        {
            SentrySdk.Init(options =>
            {
                options.Dsn = dsn;
                options.Debug = IsDebugBuild();
                options.TracesSampleRate = IsDebugBuild() ? 1.0 : 0.2; // 20% in production
                options.Release = $"com.oximy.windows@{Constants.Version}";
                options.Environment = IsDebugBuild() ? "development" : "production";
                options.MaxBreadcrumbs = 200;
                options.AttachStacktrace = true;
                options.SendDefaultPii = false;

                // Auto session tracking
                options.AutoSessionTracking = true;

                // Don't send events in debug mode unless explicitly enabled
                if (IsDebugBuild() && Environment.GetEnvironmentVariable("SENTRY_DEBUG_SEND") != "1")
                {
                    options.SetBeforeSend((@event, hint) =>
                    {
                        Debug.WriteLine($"[SentryService] Would send event: {@event.EventId}");
                        return null; // Don't send in debug
                    });
                }
            });

            _initialized = true;
            Debug.WriteLine("[SentryService] Initialized successfully");

            // Set initial context
            ConfigureScope();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SentryService] Initialization failed: {ex.Message}");
        }
    }

    /// <summary>
    /// Configure the Sentry scope with user and device context.
    /// </summary>
    public static void ConfigureScope()
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            // User context
            scope.User = new SentryUser
            {
                Id = GetAnonymousDeviceId(),
                Username = AppState.Instance.WorkspaceName,
            };

            // Device context
            scope.SetTag("os.version", Environment.OSVersion.VersionString);
            scope.SetTag("app.version", Constants.Version);
            scope.SetTag("architecture", RuntimeInformation.ProcessArchitecture.ToString());
            scope.SetTag("device_model", Environment.MachineName);
            scope.SetTag("component", "dotnet");
            scope.SetTag("session_id", OximyLogger.SessionId);

            // App state context
            scope.SetTag("app.phase", AppState.Instance.Phase.ToString());

            // MDM context
            try
            {
                scope.SetTag("is_mdm_managed", MDMConfigService.Instance.IsManagedDevice.ToString().ToLowerInvariant());
            }
            catch
            {
                scope.SetTag("is_mdm_managed", "false");
            }
        });
    }

    /// <summary>
    /// Update user context when workspace changes.
    /// </summary>
    public static void UpdateUserContext()
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.User = new SentryUser
            {
                Id = AppState.Instance.DeviceId,
                Username = AppState.Instance.WorkspaceName,
            };
        });
    }

    /// <summary>
    /// Set full user context with workspace and device details.
    /// Called on login/enrollment completion.
    /// </summary>
    public static void SetFullUserContext(string? workspaceName, string? deviceId, string? workspaceId, string? tenantId = null)
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.User = new SentryUser
            {
                Id = deviceId ?? GetAnonymousDeviceId(),
                Username = workspaceName,
            };

            if (!string.IsNullOrEmpty(deviceId))
                scope.SetTag("device_id", deviceId);
            if (!string.IsNullOrEmpty(workspaceId))
                scope.SetTag("workspace_id", workspaceId);
            if (!string.IsNullOrEmpty(workspaceName))
                scope.SetTag("workspace_name", workspaceName);
            if (!string.IsNullOrEmpty(tenantId))
                scope.SetTag("tenant_id", tenantId);
        });
    }

    /// <summary>
    /// Clear user context on logout.
    /// </summary>
    public static void ClearUser()
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.User = new SentryUser { Id = GetAnonymousDeviceId() };
        });
    }

    /// <summary>
    /// Update app phase in context.
    /// </summary>
    public static void UpdatePhase(Phase phase)
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag("app.phase", phase.ToString());
        });
    }

    /// <summary>
    /// Update proxy status in context.
    /// </summary>
    public static void UpdateProxyStatus(bool enabled, int? port)
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag("proxy.enabled", enabled.ToString());
            if (port.HasValue)
                scope.SetTag("proxy.port", port.Value.ToString());
        });
    }

    /// <summary>
    /// Add a navigation breadcrumb.
    /// </summary>
    public static void AddNavigationBreadcrumb(string from, string to)
    {
        if (!_initialized)
            return;

        SentrySdk.AddBreadcrumb(
            message: $"Navigated from {from} to {to}",
            category: "navigation",
            level: BreadcrumbLevel.Info,
            data: new Dictionary<string, string>
            {
                ["from"] = from,
                ["to"] = to
            });
    }

    /// <summary>
    /// Add a user action breadcrumb.
    /// </summary>
    public static void AddUserActionBreadcrumb(string action, string target)
    {
        if (!_initialized)
            return;

        SentrySdk.AddBreadcrumb(
            message: $"{action}: {target}",
            category: "user",
            level: BreadcrumbLevel.Info,
            data: new Dictionary<string, string>
            {
                ["action"] = action,
                ["target"] = target
            });
    }

    /// <summary>
    /// Add a state change breadcrumb.
    /// </summary>
    public static void AddStateChangeBreadcrumb(string category, string message, Dictionary<string, string>? data = null)
    {
        if (!_initialized)
            return;

        SentrySdk.AddBreadcrumb(
            message: message,
            category: category,
            level: BreadcrumbLevel.Info,
            data: data);
    }

    /// <summary>
    /// Add an error breadcrumb.
    /// </summary>
    public static void AddErrorBreadcrumb(string service, string errorMessage)
    {
        if (!_initialized)
            return;

        SentrySdk.AddBreadcrumb(
            message: errorMessage,
            category: service,
            level: BreadcrumbLevel.Error);
    }

    /// <summary>
    /// Capture an exception with additional context.
    /// </summary>
    public static void CaptureException(Exception exception, string? errorCategory = null, Dictionary<string, string>? extras = null)
    {
        if (!_initialized)
        {
            Debug.WriteLine($"[SentryService] Would capture exception: {exception.Message}");
            return;
        }

        using (SentrySdk.PushScope())
        {
            SentrySdk.ConfigureScope(scope =>
            {
                if (!string.IsNullOrEmpty(errorCategory))
                    scope.SetTag("error_category", errorCategory);

                if (extras != null)
                {
                    foreach (var kvp in extras)
                    {
                        scope.SetExtra(kvp.Key, kvp.Value);
                    }
                }
            });

            SentrySdk.CaptureException(exception);
        }
    }

    /// <summary>
    /// Capture a message.
    /// </summary>
    public static void CaptureMessage(string message, SentryLevel level = SentryLevel.Info)
    {
        if (!_initialized)
        {
            Debug.WriteLine($"[SentryService] Would capture message: {message}");
            return;
        }

        SentrySdk.CaptureMessage(message, level);
    }

    /// <summary>
    /// Start a performance transaction.
    /// </summary>
    public static ITransactionTracer? StartTransaction(string name, string operation)
    {
        if (!_initialized)
            return null;

        return SentrySdk.StartTransaction(name, operation);
    }

    /// <summary>
    /// Flush pending events before shutdown.
    /// </summary>
    public static void Flush(TimeSpan? timeout = null)
    {
        if (!_initialized)
            return;

        try
        {
            SentrySdk.Flush(timeout ?? TimeSpan.FromSeconds(2));
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SentryService] Flush error: {ex.Message}");
        }
    }

    /// <summary>
    /// Close Sentry SDK.
    /// </summary>
    public static void Close()
    {
        if (!_initialized)
            return;

        try
        {
            SentrySdk.Close();
            _initialized = false;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SentryService] Close error: {ex.Message}");
        }
    }

    /// <summary>
    /// Get or create an anonymous device ID for tracking.
    /// </summary>
    private static string GetAnonymousDeviceId()
    {
        if (_anonymousDeviceId != null)
            return _anonymousDeviceId;

        // Try to get from settings
        var settings = Properties.Settings.Default;
        if (!string.IsNullOrEmpty(settings.DeviceId))
        {
            _anonymousDeviceId = settings.DeviceId;
        }
        else
        {
            // Generate a new one based on machine name
            _anonymousDeviceId = Convert.ToBase64String(
                System.Security.Cryptography.SHA256.HashData(
                    System.Text.Encoding.UTF8.GetBytes(Environment.MachineName + Environment.UserName)));
        }

        return _anonymousDeviceId;
    }

    private static bool IsDebugBuild()
    {
#if DEBUG
        return true;
#else
        return false;
#endif
    }
}

/// <summary>
/// Secrets configuration. Override with actual values in Secrets.cs (not committed to repo).
/// </summary>
public static partial class Secrets
{
    /// <summary>
    /// Sentry DSN for error tracking.
    /// Set this in a separate Secrets.cs file that is not committed to version control.
    /// </summary>
    public static string? SentryDsn => null;
}
