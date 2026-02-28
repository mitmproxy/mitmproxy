using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Non-activating floating toast that shows a single violation.
/// Top-right corner, 10s auto-dismiss. Mirror of ViolationNotificationView.swift on Mac.
/// </summary>
public partial class ViolationNotificationWindow : Window
{
    // Win32: prevent window from stealing focus
    private const int GWL_EXSTYLE    = -20;
    private const int WS_EX_NOACTIVATE = 0x08000000;

    [DllImport("user32.dll")]
    private static extern int GetWindowLong(IntPtr hwnd, int index);

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hwnd, int index, int value);

    private readonly DispatcherTimer _dismissTimer;
    private bool _hiding;

    public ViolationNotificationWindow(ViolationEntry violation)
    {
        InitializeComponent();
        PopulateUI(violation);
        PositionTopRight();

        _dismissTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(10) };
        _dismissTimer.Tick += (_, _) => HideWindow();

        Loaded += OnLoaded;
    }

    private void PopulateUI(ViolationEntry violation)
    {
        PiiIconText.Text    = violation.PiiIcon;
        PiiLabelText.Text   = violation.PiiLabel;
        HostText.Text       = violation.Host;
        DescriptionText.Text = violation.Message
            ?? $"Replaced with [{violation.DetectedType.ToUpperInvariant()}_REDACTED]";
    }

    private void PositionTopRight()
    {
        var workArea = SystemParameters.WorkArea;
        Left = workArea.Right - Width - 16;
        Top  = workArea.Top + 16;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        // Prevent focus steal
        var hwnd = new WindowInteropHelper(this).Handle;
        var style = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE);

        // Slide + fade in
        var fadeIn = new DoubleAnimation(0, 1, TimeSpan.FromSeconds(0.3));
        var slideIn = new DoubleAnimation(20, 0, TimeSpan.FromSeconds(0.3))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };

        BeginAnimation(OpacityProperty, fadeIn);
        SlideTransform.BeginAnimation(TranslateTransform.YProperty, slideIn);

        _dismissTimer.Start();
    }

    private void HideWindow()
    {
        if (_hiding) return;
        _hiding = true;
        _dismissTimer.Stop();

        var fadeOut = new DoubleAnimation(1, 0, TimeSpan.FromSeconds(0.25));
        var slideOut = new DoubleAnimation(0, 20, TimeSpan.FromSeconds(0.25));
        slideOut.Completed += (_, _) => Close();

        BeginAnimation(OpacityProperty, fadeOut);
        SlideTransform.BeginAnimation(TranslateTransform.YProperty, slideOut);
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => HideWindow();

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        // Set WS_EX_NOACTIVATE early (before Loaded) for maximum reliability
        var hwnd = new WindowInteropHelper(this).Handle;
        var style = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE);
    }
}
