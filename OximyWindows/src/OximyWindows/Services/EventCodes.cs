namespace OximyWindows.Services;

// MARK: - Log Level

public enum LogLevel
{
    Debug = 0,
    Info = 1,
    Warning = 2,
    Error = 3,
    Fatal = 4
}

// MARK: - Action Category

public enum ActionCategory
{
    None,
    Monitor,
    AutoRetry,
    SelfHealing,
    Investigate,
    AlertOps,
    UserAction
}

// MARK: - Event Code

/// <summary>
/// Every log event gets a unique code: SVC.OPS.NNN
/// - SVC = service (APP, AUTH, ENROLL, CERT, PROXY, MITM, HB, NET, SYNC, STATE, LAUNCH, SYS)
/// - OPS = operation (INIT, START, STOP, FAIL, RETRY, STATE, CB, CMD, AUTH, CLEAN, FETCH, HEALTH, CHECK)
/// - NNN = unique ID (0xx=lifecycle, 1xx=state, 2xx=warning, 3xx=error, 4xx=fatal)
/// </summary>
public enum EventCode
{
    // App
    APP_INIT_001,
    APP_STATE_101,
    APP_START_001,
    APP_STOP_001,
    APP_FAIL_301,

    // Auth
    AUTH_AUTH_001,
    AUTH_AUTH_002,
    AUTH_AUTH_004,
    AUTH_FAIL_201,
    AUTH_FAIL_301,
    AUTH_FAIL_302,
    AUTH_FAIL_303,

    // Enrollment
    ENROLL_STATE_101,
    ENROLL_FAIL_301,

    // Certificate
    CERT_STATE_101,
    CERT_STATE_102,
    CERT_STATE_105,
    CERT_CHECK_003,
    CERT_WARN_201,
    CERT_FAIL_301,
    CERT_FAIL_303,

    // Proxy
    PROXY_START_001,
    PROXY_STOP_001,
    PROXY_CLEAN_001,
    PROXY_STATE_002,
    PROXY_FAIL_301,

    // MITM
    MITM_START_002,
    MITM_STOP_001,
    MITM_FAIL_301,
    MITM_FAIL_304,
    MITM_FAIL_306,
    MITM_RETRY_001,
    MITM_RETRY_401,

    // Heartbeat
    HB_FETCH_001,
    HB_FAIL_201,
    HB_FAIL_202,
    HB_FAIL_203,
    HB_STATE_202,
    HB_CMD_002,

    // Network
    NET_STATE_102,
    NET_STATE_103,
    NET_STATE_104,
    NET_FAIL_301,

    // Sync
    SYNC_FAIL_201,

    // Remote State
    STATE_STATE_001,
    STATE_CMD_003,
    STATE_FAIL_201,

    // Launch
    LAUNCH_FAIL_301,

    // System Health
    SYS_HEALTH_001,
}

// MARK: - Extension Methods

public static class EventCodeExtensions
{
    /// <summary>
    /// Returns the dot-separated code string, e.g. "APP.INIT.001".
    /// </summary>
    public static string GetCode(this EventCode code)
    {
        var name = code.ToString(); // e.g. "APP_INIT_001"
        var parts = name.Split('_');
        return string.Join(".", parts);
    }

    /// <summary>
    /// Returns the severity level for this event code.
    /// </summary>
    public static LogLevel GetLevel(this EventCode code) => code switch
    {
        // Fatal
        EventCode.MITM_RETRY_401 => LogLevel.Fatal,

        // Error
        EventCode.APP_FAIL_301 or
        EventCode.AUTH_FAIL_301 or
        EventCode.ENROLL_FAIL_301 or
        EventCode.CERT_FAIL_301 or EventCode.CERT_FAIL_303 or
        EventCode.PROXY_FAIL_301 or
        EventCode.MITM_FAIL_301 or EventCode.MITM_FAIL_304 or EventCode.MITM_FAIL_306 or
        EventCode.NET_FAIL_301 or
        EventCode.LAUNCH_FAIL_301 => LogLevel.Error,

        // Warning
        EventCode.AUTH_AUTH_004 or
        EventCode.AUTH_FAIL_201 or EventCode.AUTH_FAIL_302 or EventCode.AUTH_FAIL_303 or
        EventCode.CERT_WARN_201 or
        EventCode.PROXY_CLEAN_001 or
        EventCode.MITM_RETRY_001 or
        EventCode.HB_FAIL_201 or EventCode.HB_FAIL_202 or EventCode.HB_FAIL_203 or EventCode.HB_STATE_202 or
        EventCode.SYNC_FAIL_201 or
        EventCode.STATE_CMD_003 or EventCode.STATE_FAIL_201 => LogLevel.Warning,

        // Info (default)
        _ => LogLevel.Info,
    };

    /// <summary>
    /// Returns the action category for this event code.
    /// </summary>
    public static ActionCategory GetAction(this EventCode code) => code switch
    {
        EventCode.MITM_RETRY_401 => ActionCategory.AlertOps,

        EventCode.AUTH_AUTH_004 or EventCode.AUTH_FAIL_301 or
        EventCode.CERT_FAIL_303 or EventCode.ENROLL_FAIL_301 or
        EventCode.STATE_CMD_003 => ActionCategory.UserAction,

        EventCode.APP_FAIL_301 or
        EventCode.AUTH_FAIL_302 or EventCode.AUTH_FAIL_303 or
        EventCode.CERT_FAIL_301 or EventCode.PROXY_FAIL_301 or
        EventCode.MITM_FAIL_301 or
        EventCode.HB_FAIL_202 or EventCode.HB_STATE_202 or
        EventCode.LAUNCH_FAIL_301 => ActionCategory.Investigate,

        EventCode.MITM_FAIL_304 or EventCode.MITM_FAIL_306 or
        EventCode.MITM_RETRY_001 or
        EventCode.AUTH_FAIL_201 => ActionCategory.AutoRetry,

        EventCode.CERT_STATE_105 or
        EventCode.PROXY_CLEAN_001 => ActionCategory.SelfHealing,

        EventCode.HB_FAIL_201 or EventCode.HB_FAIL_203 or
        EventCode.SYNC_FAIL_201 or
        EventCode.STATE_FAIL_201 or
        EventCode.NET_STATE_102 => ActionCategory.Monitor,

        _ => ActionCategory.None,
    };

    /// <summary>
    /// Returns the service segment (first part, lowercased).
    /// </summary>
    public static string GetService(this EventCode code)
    {
        var dotCode = code.GetCode();
        var idx = dotCode.IndexOf('.');
        return idx > 0 ? dotCode[..idx].ToLowerInvariant() : "unknown";
    }

    /// <summary>
    /// Returns the operation segment (second part, lowercased).
    /// </summary>
    public static string GetOperation(this EventCode code)
    {
        var parts = code.GetCode().Split('.');
        return parts.Length > 1 ? parts[1].ToLowerInvariant() : "unknown";
    }

    /// <summary>
    /// Returns the action category as a snake_case string for JSONL/Sentry.
    /// </summary>
    public static string GetActionString(this ActionCategory action) => action switch
    {
        ActionCategory.None => "none",
        ActionCategory.Monitor => "monitor",
        ActionCategory.AutoRetry => "auto_retry",
        ActionCategory.SelfHealing => "self_healing",
        ActionCategory.Investigate => "investigate",
        ActionCategory.AlertOps => "alert_ops",
        ActionCategory.UserAction => "user_action",
        _ => "none",
    };
}
