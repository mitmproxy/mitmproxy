using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using System.Web;
using System.Windows;
using Microsoft.Win32;
using OximyWindows.Core;
using OximyWindows.Services;
using OximyWindows.Views;

namespace OximyWindows;

public partial class App : Application
{
    private static Mutex? _mutex;
    private MainWindow? _mainWindow;
    private static TextWriterTraceListener? _fileTraceListener;
    private string? _pendingAuthUrl;

    // Core Services
    public static MitmService MitmService { get; } = new();
    public static ProxyService ProxyService { get; } = new();
    public static CertificateService CertificateService { get; } = new();
    public static NetworkMonitorService NetworkMonitorService { get; } = new();
    public static StartupService StartupService { get; } = new();

    // New Services for Mac parity
    public static APIClient APIClient => APIClient.Instance;
    public static HeartbeatService HeartbeatService => HeartbeatService.Instance;
    public static SyncService SyncService => SyncService.Instance;
    public static RemoteStateService RemoteStateService => RemoteStateService.Instance;

    /// <summary>
    /// Path to the debug log file.
    /// </summary>
    public static string LogFilePath => Path.Combine(Constants.LogsDir, "oximy-debug.log");

    protected override void OnStartup(StartupEventArgs e)
    {
        // Set up file logging for Debug output
        SetupFileLogging();

        // CRITICAL: Initialize Sentry SECOND, before any other code that might throw.
        // This ensures we capture any startup errors.
        SentryService.Initialize();

        // Single instance check
        const string mutexName = "OximyWindowsSingleInstance";
        _mutex = new Mutex(true, mutexName, out var createdNew);

        if (!createdNew)
        {
            // Another instance is running
            MessageBox.Show("Oximy is already running.", "Oximy", MessageBoxButton.OK, MessageBoxImage.Information);
            Shutdown();
            return;
        }

        // Register oximy:// URL scheme for deep linking
        RegisterUrlScheme();

        // Handle deep link if launched via oximy:// URL
        if (e.Args.Length > 0 && e.Args[0].StartsWith("oximy://", StringComparison.OrdinalIgnoreCase))
        {
            // Store the URL to handle after main window is created
            _pendingAuthUrl = e.Args[0];
        }

        base.OnStartup(e);

        // Ensure directories exist
        Constants.EnsureDirectoriesExist();

        // Initialize services
        CertificateService.CheckStatus();
        ProxyService.CheckStatus();
        StartupService.CheckStatus();

        // Update Sentry context with initial state
        SentryService.UpdatePhase(AppState.Instance.Phase);
        SentryService.UpdateProxyStatus(ProxyService.IsProxyEnabled, MitmService.CurrentPort);

        // Handle session ending (logout, shutdown, restart)
        SystemEvents.SessionEnding += OnSessionEnding;

        // Handle unhandled exceptions
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        DispatcherUnhandledException += OnDispatcherUnhandledException;

        // Create and show main window (hidden, hosts tray icon)
        _mainWindow = new MainWindow();

        // Subscribe to service events
        HeartbeatService.LogoutRequested += OnLogoutRequested;
        HeartbeatService.RestartProxyRequested += OnRestartProxyRequested;
        HeartbeatService.DisableProxyRequested += OnDisableProxyRequested;

        // Start remote state monitoring
        RemoteStateService.Start();
        RemoteStateService.ForceLogoutRequested += OnForceLogoutRequested;
        RemoteStateService.SensorEnabledChanged += OnSensorStateChanged;

        // Auto-enable launch at startup on first run
        StartupService.CheckAndAutoEnableOnFirstLaunch();

        // Start services if already connected
        if (AppState.Instance.Phase == Phase.Connected)
        {
            HeartbeatService.Start();
            SyncService.Start();
        }

        // Handle pending auth URL if launched via deep link
        if (!string.IsNullOrEmpty(_pendingAuthUrl))
        {
            HandleAuthCallback(_pendingAuthUrl);
            _pendingAuthUrl = null;
        }

        // Note: Auto-update disabled for MDM deployment
    }

    private void OnLogoutRequested(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() =>
        {
            Debug.WriteLine("[App] Logout requested by server");
            ProxyService.DisableProxy();
            MitmService.Stop();
            HeartbeatService.Stop();
            SyncService.Stop();
            AppState.Instance.Logout();
        });
    }

    private async void OnRestartProxyRequested(object? sender, EventArgs e)
    {
        Debug.WriteLine("[App] Restart proxy requested by server");
        await MitmService.RestartAsync();
    }

    private void OnDisableProxyRequested(object? sender, EventArgs e)
    {
        Debug.WriteLine("[App] Disable proxy requested by server");
        ProxyService.DisableProxy();
        MitmService.Stop();
    }

    private void OnForceLogoutRequested(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() => OnLogoutRequested(sender, e));
    }

    private void OnSensorStateChanged(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() => _mainWindow?.UpdateTrayIcon(RemoteStateService.SensorEnabled));
    }

    /// <summary>
    /// Register the oximy:// URL scheme in Windows Registry.
    /// This allows the browser to redirect back to our app after authentication.
    /// </summary>
    private void RegisterUrlScheme()
    {
        try
        {
            var exePath = Process.GetCurrentProcess().MainModule?.FileName;
            if (string.IsNullOrEmpty(exePath)) return;

            using var key = Registry.CurrentUser.CreateSubKey(@"Software\Classes\oximy");
            if (key == null) return;

            key.SetValue("", "URL:Oximy Protocol");
            key.SetValue("URL Protocol", "");

            using var shellKey = key.CreateSubKey(@"shell\open\command");
            shellKey?.SetValue("", $"\"{exePath}\" \"%1\"");

            Debug.WriteLine("[App] URL scheme registered successfully");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[App] Failed to register URL scheme: {ex.Message}");
        }
    }

    /// <summary>
    /// Handle authentication callback from browser redirect.
    /// URL format: oximy://auth/callback?token=xxx&state=xxx&workspace_name=xxx&device_id=xxx
    /// </summary>
    private void HandleAuthCallback(string url)
    {
        Debug.WriteLine($"[App] Received auth callback: {url}");

        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri))
        {
            Debug.WriteLine("[App] Invalid URL format");
            return;
        }

        if (uri.Scheme != "oximy" || uri.Host != "auth" || uri.AbsolutePath != "/callback")
        {
            Debug.WriteLine("[App] URL doesn't match auth callback pattern");
            return;
        }

        var query = HttpUtility.ParseQueryString(uri.Query);
        var token = query["token"];
        var state = query["state"];
        var workspaceName = query["workspace_name"];
        var deviceId = query["device_id"];

        // Validate CSRF state
        var storedState = OximyWindows.Properties.Settings.Default.AuthState;
        if (state != storedState)
        {
            Debug.WriteLine($"[App] State mismatch - stored: {storedState}, received: {state}");
            return;
        }

        // Clear stored state
        OximyWindows.Properties.Settings.Default.AuthState = "";
        OximyWindows.Properties.Settings.Default.Save();

        if (string.IsNullOrEmpty(token))
        {
            Debug.WriteLine("[App] No token in callback URL");
            return;
        }

        // Complete enrollment
        var workspace = workspaceName ?? "Connected";
        AppState.Instance.CompleteEnrollment(deviceId ?? "", token, workspace, "");

        SentryService.AddStateChangeBreadcrumb(
            category: "enrollment",
            message: "Device enrolled via browser auth",
            data: new Dictionary<string, string> { ["deviceId"] = deviceId ?? "unknown" });

        Debug.WriteLine("[App] Auth callback processed successfully");

        // Start services in background (certificate, mitmproxy, heartbeat, sync)
        _ = StartServicesAfterEnrollmentAsync();

        // Show the popup so user sees they're logged in
        _mainWindow?.ShowPopup();
    }

    /// <summary>
    /// Start all services after enrollment completes.
    /// Certificate installation and mitmproxy startup happen in background.
    /// </summary>
    private async Task StartServicesAfterEnrollmentAsync()
    {
        Debug.WriteLine("[App] Starting services after enrollment...");

        // Install certificate in background (will prompt user via Windows UAC if needed)
        CertificateService.CheckStatus();
        if (!CertificateService.IsCAInstalled)
        {
            try
            {
                await CertificateService.InstallCAAsync();
                Debug.WriteLine("[App] Certificate installed after enrollment");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[App] Certificate install failed (user can retry from settings): {ex.Message}");
                // Don't block - user can install from settings later
            }
        }

        // Start mitmproxy
        if (!MitmService.IsRunning)
        {
            try
            {
                await MitmService.StartAsync();
                Debug.WriteLine("[App] MitmService started after enrollment");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[App] MitmService start failed: {ex.Message}");
            }
        }

        // Start heartbeat and sync services
        HeartbeatService.Start();
        SyncService.Start();
        Debug.WriteLine("[App] All services started after enrollment");
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Debug.WriteLine("[App] Exiting, performing cleanup...");

        // Flush pending events before shutdown
        try
        {
            Debug.WriteLine("[App] Flushing pending events...");
            SyncService.FlushSync(timeoutMs: 5000);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[App] Event flush error: {ex.Message}");
        }

        // Stop background services
        try
        {
            HeartbeatService.Stop();
            SyncService.Stop();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[App] Service stop error: {ex.Message}");
        }

        // Critical cleanup - always disable proxy and stop mitmproxy
        try
        {
            ProxyService.DisableProxy();
            MitmService.Stop();
        }
        catch
        {
            // Ignore errors during shutdown
        }

        // Stop and dispose services
        RemoteStateService.Stop();
        MitmService.Dispose();
        NetworkMonitorService.Dispose();
        HeartbeatService.Dispose();
        SyncService.Dispose();
        RemoteStateService.Dispose();

        // Unsubscribe from system events
        SystemEvents.SessionEnding -= OnSessionEnding;
        HeartbeatService.LogoutRequested -= OnLogoutRequested;
        HeartbeatService.RestartProxyRequested -= OnRestartProxyRequested;
        HeartbeatService.DisableProxyRequested -= OnDisableProxyRequested;
        RemoteStateService.ForceLogoutRequested -= OnForceLogoutRequested;
        RemoteStateService.SensorEnabledChanged -= OnSensorStateChanged;

        _mutex?.ReleaseMutex();
        _mutex?.Dispose();

        // Flush and close Sentry
        SentryService.Flush(TimeSpan.FromSeconds(2));
        SentryService.Close();

        // Clean up file logging
        CleanupFileLogging();

        Debug.WriteLine("[App] Cleanup complete");
        base.OnExit(e);
    }

    /// <summary>
    /// Set up file logging so Debug.WriteLine output goes to a log file.
    /// </summary>
    private static void SetupFileLogging()
    {
        try
        {
            // Ensure directory exists
            Directory.CreateDirectory(Constants.LogsDir);

            // Create a file stream for logging
            var logStream = new FileStream(LogFilePath, FileMode.Create, FileAccess.Write, FileShare.Read);
            _fileTraceListener = new TextWriterTraceListener(logStream)
            {
                TraceOutputOptions = TraceOptions.DateTime
            };

            Trace.Listeners.Add(_fileTraceListener);
            // Disable AutoFlush to avoid synchronous disk I/O on every Debug.WriteLine
            // We manually flush on exit and periodically via a timer
            Trace.AutoFlush = false;

            Debug.WriteLine($"[App] Logging started at {DateTime.Now}");
            Debug.WriteLine($"[App] Log file: {LogFilePath}");
            Debug.WriteLine($"[App] API Base URL: {Constants.ApiBaseUrl}");
        }
        catch (Exception ex)
        {
            // Silently fail - logging is optional
            System.Diagnostics.Debug.WriteLine($"Failed to set up file logging: {ex.Message}");
        }
    }

    /// <summary>
    /// Clean up file logging on exit.
    /// </summary>
    private static void CleanupFileLogging()
    {
        try
        {
            _fileTraceListener?.Flush();
            _fileTraceListener?.Close();
            _fileTraceListener?.Dispose();
            Trace.Listeners.Remove(_fileTraceListener!);
        }
        catch
        {
            // Ignore cleanup errors
        }
    }

    private void OnSessionEnding(object sender, SessionEndingEventArgs e)
    {
        // Windows is logging off or shutting down
        try
        {
            ProxyService.DisableProxy();
            MitmService.Stop();
        }
        catch
        {
            // Ignore errors during shutdown
        }
    }

    private void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        // Capture exception in Sentry
        if (e.ExceptionObject is Exception ex)
        {
            SentryService.CaptureException(ex, "crash");
            SentryService.Flush(TimeSpan.FromSeconds(2));
        }

        // Try to clean up before crash
        try
        {
            ProxyService.DisableProxy();
            MitmService.Stop();
        }
        catch
        {
            // Ignore errors during crash handling
        }
    }

    private void OnDispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
    {
        // Capture exception in Sentry
        SentryService.CaptureException(e.Exception, "ui");

        // Log the error
        Debug.WriteLine($"Unhandled exception: {e.Exception}");

        // Show error message
        MessageBox.Show(
            $"An unexpected error occurred: {e.Exception.Message}\n\nThe application will attempt to continue.",
            "Oximy Error",
            MessageBoxButton.OK,
            MessageBoxImage.Error);

        e.Handled = true;
    }

    public static void Quit()
    {
        Current.Shutdown();
    }
}
