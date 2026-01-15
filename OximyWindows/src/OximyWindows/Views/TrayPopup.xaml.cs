using System.Windows;
using System.Windows.Controls;
using System.Windows.Forms;
using System.Windows.Interop;
using Hardcodet.Wpf.TaskbarNotification;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class TrayPopup : Window
{
    // Track current phase to detect major transitions
    private Phase _lastPhase = Phase.Enrollment;

    public TrayPopup()
    {
        InitializeComponent();

        // Subscribe to phase changes
        AppState.Instance.PropertyChanged += OnAppStateChanged;

        // Set initial content
        _lastPhase = AppState.Instance.Phase;
        UpdateContent();
    }

    private void OnAppStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(AppState.Phase))
        {
            // Use BeginInvoke to avoid deadlock (non-blocking)
            Dispatcher.BeginInvoke(UpdateContent);
        }
    }

    private void UpdateContent()
    {
        var newPhase = AppState.Instance.Phase;

        // Create fresh view for the phase (don't cache to avoid stale state issues on logout)
        ContentHost.Content = newPhase switch
        {
            Phase.Enrollment or Phase.Onboarding or Phase.Login => new EnrollmentView(),
            Phase.Setup or Phase.Permissions => new SetupView(),
            Phase.Connected or Phase.Ready => new StatusView(),
            _ => new StatusView()
        };

        _lastPhase = newPhase;
    }

    /// <summary>
    /// Refresh the popup content based on current phase.
    /// </summary>
    public void RefreshContent()
    {
        UpdateContent();
        Show();
        Activate();
    }

    /// <summary>
    /// Show the popup near the system tray icon.
    /// </summary>
    public void ShowNearTray(TaskbarIcon trayIcon)
    {
        // Get screen info
        var screen = Screen.PrimaryScreen ?? Screen.AllScreens[0];
        var workArea = screen.WorkingArea;
        var taskbarPosition = GetTaskbarPosition(screen);

        // Calculate position based on taskbar location
        double left, top;

        switch (taskbarPosition)
        {
            case TaskbarPosition.Bottom:
                // Position above taskbar, aligned to right
                left = workArea.Right - Width - 10;
                top = workArea.Bottom - Height - 10;
                break;

            case TaskbarPosition.Top:
                // Position below taskbar, aligned to right
                left = workArea.Right - Width - 10;
                top = workArea.Top + 10;
                break;

            case TaskbarPosition.Right:
                // Position to left of taskbar
                left = workArea.Right - Width - 10;
                top = workArea.Bottom - Height - 10;
                break;

            case TaskbarPosition.Left:
                // Position to right of taskbar
                left = workArea.Left + 10;
                top = workArea.Bottom - Height - 10;
                break;

            default:
                // Default to bottom-right
                left = workArea.Right - Width - 10;
                top = workArea.Bottom - Height - 10;
                break;
        }

        // Convert to WPF units (handle DPI)
        var source = PresentationSource.FromVisual(this);
        if (source?.CompositionTarget != null)
        {
            var dpiX = source.CompositionTarget.TransformToDevice.M11;
            var dpiY = source.CompositionTarget.TransformToDevice.M22;

            left /= dpiX;
            top /= dpiY;
        }

        Left = left;
        Top = top;

        Show();
        Activate();
    }

    private void Window_Deactivated(object sender, EventArgs e)
    {
        // Hide popup when clicking outside (unless it's a critical phase)
        if (AppState.Instance.Phase == Phase.Connected)
        {
            Hide();
        }
    }

    private static TaskbarPosition GetTaskbarPosition(Screen screen)
    {
        var screenBounds = screen.Bounds;
        var workArea = screen.WorkingArea;

        if (workArea.Top > screenBounds.Top)
            return TaskbarPosition.Top;
        if (workArea.Bottom < screenBounds.Bottom)
            return TaskbarPosition.Bottom;
        if (workArea.Left > screenBounds.Left)
            return TaskbarPosition.Left;
        if (workArea.Right < screenBounds.Right)
            return TaskbarPosition.Right;

        return TaskbarPosition.Bottom; // Default
    }

    private enum TaskbarPosition
    {
        Bottom,
        Top,
        Left,
        Right
    }

    protected override void OnClosed(EventArgs e)
    {
        AppState.Instance.PropertyChanged -= OnAppStateChanged;
        base.OnClosed(e);
    }
}
