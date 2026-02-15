using System.Diagnostics;
using System.Runtime.InteropServices;
using OximyWindows.Core;
using Sentry;

namespace OximyWindows.Services;

public static class SentryService
{
    private static bool _initialized;
    private static string? _anonymousDeviceId;

#if DEBUG
    private static readonly bool _isDebug = true;
#else
    private static readonly bool _isDebug = false;
#endif

    public static bool IsInitialized => _initialized;

    public static void Initialize()
    {
        if (_initialized)
            return;

        var dsn = Environment.GetEnvironmentVariable("BETTERSTACK_ERRORS_DSN")
                ?? Environment.GetEnvironmentVariable("SENTRY_DSN")
                ?? Secrets.SentryDsn;
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
                options.Debug = _isDebug;
                options.TracesSampleRate = _isDebug ? 1.0 : 0.2;
                options.Release = $"com.oximy.windows@{Constants.Version}";
                options.Environment = _isDebug ? "development" : "production";
                options.MaxBreadcrumbs = 200;
                options.AttachStacktrace = true;
                options.SendDefaultPii = false;
                options.AutoSessionTracking = true;
            });

            _initialized = true;
            Debug.WriteLine("[SentryService] Initialized successfully");
            ConfigureScope();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SentryService] Initialization failed: {ex.Message}");
        }
    }

    public static void ConfigureScope()
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.User = new SentryUser
            {
                Id = GetAnonymousDeviceId(),
                Username = AppState.Instance.WorkspaceName,
            };

            scope.SetTag("os.version", Environment.OSVersion.VersionString);
            scope.SetTag("app.version", Constants.Version);
            scope.SetTag("architecture", RuntimeInformation.ProcessArchitecture.ToString());
            scope.SetTag("device_model", Environment.MachineName);
            scope.SetTag("component", "dotnet");
            scope.SetTag("session_id", OximyLogger.SessionId);
            scope.SetTag("app.phase", AppState.Instance.Phase.ToString());

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

    public static void ClearUser()
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.User = new SentryUser { Id = GetAnonymousDeviceId() };
        });
    }

    public static void UpdateSetupStatus(bool complete)
    {
        if (!_initialized) return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag("setup_status", complete ? "complete" : "in_progress");
        });
    }

    public static void UpdatePhase(Phase phase)
    {
        if (!_initialized)
            return;

        SentrySdk.ConfigureScope(scope =>
        {
            scope.SetTag("app.phase", phase.ToString());
        });
    }

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

    public static void AddErrorBreadcrumb(string service, string errorMessage)
    {
        if (!_initialized)
            return;

        SentrySdk.AddBreadcrumb(
            message: errorMessage,
            category: service,
            level: BreadcrumbLevel.Error);
    }

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

    public static void CaptureMessage(string message, SentryLevel level = SentryLevel.Info)
    {
        if (!_initialized)
        {
            Debug.WriteLine($"[SentryService] Would capture message: {message}");
            return;
        }

        SentrySdk.CaptureMessage(message, level);
    }

    public static ITransactionTracer? StartTransaction(string name, string operation)
    {
        if (!_initialized)
            return null;

        return SentrySdk.StartTransaction(name, operation);
    }

    public static void Flush()
    {
        if (!_initialized)
            return;

        try
        {
            SentrySdk.Flush(TimeSpan.FromSeconds(2));
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[SentryService] Flush error: {ex.Message}");
        }
    }

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

    private static string GetAnonymousDeviceId()
    {
        if (_anonymousDeviceId != null)
            return _anonymousDeviceId;

        var settings = Properties.Settings.Default;
        _anonymousDeviceId = !string.IsNullOrEmpty(settings.DeviceId)
            ? settings.DeviceId
            : Convert.ToBase64String(
                System.Security.Cryptography.SHA256.HashData(
                    System.Text.Encoding.UTF8.GetBytes(Environment.MachineName + Environment.UserName)));

        return _anonymousDeviceId;
    }
}
