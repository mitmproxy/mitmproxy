namespace OximyWindows.Core;

/// <summary>
/// Application phases representing the onboarding and usage flow.
/// Matches the Mac app's three-phase flow: Enrollment -> Setup -> Ready
/// </summary>
public enum Phase
{
    /// <summary>
    /// Initial welcome and privacy information screens (legacy).
    /// </summary>
    Onboarding,

    /// <summary>
    /// 6-digit workspace code authentication.
    /// Step 1: User enters enrollment code to connect to workspace.
    /// </summary>
    Enrollment,

    /// <summary>
    /// Certificate installation and proxy configuration.
    /// Step 2: Setup certificate and proxy before monitoring.
    /// </summary>
    Setup,

    /// <summary>
    /// Legacy alias for Enrollment.
    /// </summary>
    Login,

    /// <summary>
    /// Legacy alias for Setup.
    /// </summary>
    Permissions,

    /// <summary>
    /// Main running state - monitoring AI traffic.
    /// Dashboard with Home/Settings/Support tabs.
    /// </summary>
    Connected,

    /// <summary>
    /// Alias for Connected - ready to monitor.
    /// </summary>
    Ready
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
