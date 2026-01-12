using System.Diagnostics;
using System.IO;
using System.Windows;
using Microsoft.Win32;
using OximyWindows.Core;
using OximyWindows.Services;
using OximyWindows.Views;
using Velopack;

namespace OximyWindows;

public partial class App : Application
{
    private static Mutex? _mutex;
    private MainWindow? _mainWindow;
    private static TextWriterTraceListener? _fileTraceListener;

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

    /// <summary>
    /// Path to the debug log file.
    /// </summary>
    public static string LogFilePath => Path.Combine(Constants.LogsDir, "oximy-debug.log");

    protected override void OnStartup(StartupEventArgs e)
    {
        // CRITICAL: Velopack hooks must be called FIRST before any other code.
        // This handles update installation, uninstallation, and first-run scenarios.
        VelopackApp.Build().Run();

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

        // Start services if already connected
        if (AppState.Instance.Phase == Phase.Connected)
        {
            HeartbeatService.Start();
            SyncService.Start();
        }

        // Check for updates in background after startup (5 second delay)
        Task.Run(async () =>
        {
            await Task.Delay(5000);
            await UpdateService.Instance.CheckForUpdatesAsync();
        });
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

        // Dispose services
        MitmService.Dispose();
        NetworkMonitorService.Dispose();
        HeartbeatService.Dispose();
        SyncService.Dispose();

        // Unsubscribe from system events
        SystemEvents.SessionEnding -= OnSessionEnding;
        HeartbeatService.LogoutRequested -= OnLogoutRequested;
        HeartbeatService.RestartProxyRequested -= OnRestartProxyRequested;
        HeartbeatService.DisableProxyRequested -= OnDisableProxyRequested;

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
            Trace.AutoFlush = true;

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
