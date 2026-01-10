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

    // Services
    public static MitmService MitmService { get; } = new();
    public static ProxyService ProxyService { get; } = new();
    public static CertificateService CertificateService { get; } = new();
    public static NetworkMonitorService NetworkMonitorService { get; } = new();
    public static StartupService StartupService { get; } = new();

    protected override void OnStartup(StartupEventArgs e)
    {
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

        // Handle session ending (logout, shutdown, restart)
        SystemEvents.SessionEnding += OnSessionEnding;

        // Handle unhandled exceptions
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        DispatcherUnhandledException += OnDispatcherUnhandledException;

        // Create and show main window (hidden, hosts tray icon)
        _mainWindow = new MainWindow();
    }

    protected override void OnExit(ExitEventArgs e)
    {
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

        _mutex?.ReleaseMutex();
        _mutex?.Dispose();

        base.OnExit(e);
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
        // Log the error
        System.Diagnostics.Debug.WriteLine($"Unhandled exception: {e.Exception}");

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
