namespace OximyWindows.Core;

/// <summary>
/// Application phases representing the onboarding and usage flow.
/// </summary>
public enum Phase
{
    /// <summary>
    /// Initial welcome and privacy information screens.
    /// </summary>
    Onboarding,

    /// <summary>
    /// Certificate installation and proxy enablement.
    /// </summary>
    Permissions,

    /// <summary>
    /// 6-digit workspace code authentication.
    /// </summary>
    Login,

    /// <summary>
    /// Main running state - monitoring AI traffic.
    /// </summary>
    Connected
}

/// <summary>
/// Connection status for the mitmproxy service.
/// </summary>
public enum ConnectionStatus
{
    /// <summary>
    /// Not connected, proxy disabled.
    /// </summary>
    Disconnected,

    /// <summary>
    /// Starting up mitmproxy.
    /// </summary>
    Connecting,

    /// <summary>
    /// Fully operational.
    /// </summary>
    Connected,

    /// <summary>
    /// Error state, needs attention.
    /// </summary>
    Error
}
