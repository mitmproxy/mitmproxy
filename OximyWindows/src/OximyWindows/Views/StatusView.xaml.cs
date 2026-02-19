using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using OximyWindows.Core;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Status view showing monitoring state based on RemoteStateService.
/// The toggle button has been removed - monitoring is now admin-controlled.
/// </summary>
public partial class StatusView : UserControl
{
    private readonly DispatcherTimer _refreshTimer;

    // Debouncing: coalesce rapid property changes into a single UI update
    private bool _updatePending;
    private DateTime _lastUpdateTime = DateTime.MinValue;
    private static readonly TimeSpan MinUpdateInterval = TimeSpan.FromMilliseconds(100);

    public StatusView()
    {
        InitializeComponent();

        // Set up refresh timer for events count (30 seconds is sufficient)
        _refreshTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(30)
        };
        _refreshTimer.Tick += OnRefreshTimerTick;

        Loaded += OnLoaded;
        Unloaded += OnUnloaded;
    }

    private void SubscribeToEvents()
    {
        AppState.Instance.PropertyChanged += OnAppStateChanged;
        App.RemoteStateService.PropertyChanged += OnRemoteStateChanged;
        App.MitmService.Started += OnMitmStarted;
        App.MitmService.Stopped += OnMitmStopped;
    }

    private void UnsubscribeFromEvents()
    {
        AppState.Instance.PropertyChanged -= OnAppStateChanged;
        App.RemoteStateService.PropertyChanged -= OnRemoteStateChanged;
        App.MitmService.Started -= OnMitmStarted;
        App.MitmService.Stopped -= OnMitmStopped;
    }

    private void OnMitmStarted(object? sender, EventArgs e) => ScheduleUIUpdate();
    private void OnMitmStopped(object? sender, EventArgs e) => ScheduleUIUpdate();
    private void OnRefreshTimerTick(object? sender, EventArgs e) => AppState.Instance.RefreshEventsCount();

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        SubscribeToEvents();
        UpdateUI(); // Immediate update on load
        _refreshTimer.Start();

        // Check for updates once on launch
        await UpdateCheckService.Instance.CheckOnceAsync();
        UpdateUpdateBanner();
        UpdateCheckService.Instance.UpdateStatusChanged += OnUpdateStatusChanged;
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        _refreshTimer.Stop();
        UnsubscribeFromEvents();
        UpdateCheckService.Instance.UpdateStatusChanged -= OnUpdateStatusChanged;
    }

    private void OnAppStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        ScheduleUIUpdate();
    }

    private void OnRemoteStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        ScheduleUIUpdate();
    }

    /// <summary>
    /// Schedule a debounced UI update. Multiple rapid calls are coalesced.
    /// </summary>
    private void ScheduleUIUpdate()
    {
        if (_updatePending)
            return;

        var now = DateTime.UtcNow;
        var timeSinceLastUpdate = now - _lastUpdateTime;

        if (timeSinceLastUpdate >= MinUpdateInterval)
        {
            // Enough time has passed, update immediately
            Dispatcher.BeginInvoke(UpdateUI, DispatcherPriority.Background);
        }
        else
        {
            // Too soon, schedule for later
            _updatePending = true;
            var delay = MinUpdateInterval - timeSinceLastUpdate;
            Dispatcher.BeginInvoke(async () =>
            {
                await Task.Delay(delay);
                _updatePending = false;
                UpdateUI();
            }, DispatcherPriority.Background);
        }
    }

    private async void UpdateUI()
    {
        _lastUpdateTime = DateTime.UtcNow;
        var state = AppState.Instance;

        // Update device info
        DeviceText.Text = state.DeviceName;
        WorkspaceText.Text = string.IsNullOrEmpty(state.WorkspaceName) ? "Not connected" : state.WorkspaceName;

        // Update status display
        UpdateStatusUI();

        // Update error panel
        if (state.ConnectionStatus == ConnectionStatus.Error && !string.IsNullOrEmpty(state.ErrorMessage))
        {
            ErrorText.Text = state.ErrorMessage;
            ErrorPanel.Visibility = Visibility.Visible;
        }
        else
        {
            ErrorPanel.Visibility = Visibility.Collapsed;
        }

        // Certificate status - run on background thread to avoid blocking UI
        await Task.Run(() => App.CertificateService.CheckStatus());
        CertWarningText.Visibility = App.CertificateService.IsCAInstalled ? Visibility.Collapsed : Visibility.Visible;
    }

    private void UpdateStatusUI()
    {
        var successBrush = TryFindResource("SuccessBrush") as SolidColorBrush ?? Brushes.Green;
        var warningBrush = TryFindResource("WarningBrush") as SolidColorBrush ?? Brushes.Orange;
        var yellowBrush = new SolidColorBrush(Color.FromRgb(0xFF, 0xC1, 0x07)); // Yellow for paused
        var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;
        var grayBrush = TryFindResource("TextSecondaryBrush") as SolidColorBrush ?? Brushes.Gray;

        var remote = App.RemoteStateService;
        var isCertInstalled = App.CertificateService.IsCAInstalled;
        var status = AppState.Instance.ConnectionStatus;

        // Determine status color and icon based on remote state
        SolidColorBrush statusColor;
        string statusIcon;
        string statusText;

        if (!remote.SensorEnabled)
        {
            // Monitoring Paused by Admin - Yellow
            statusColor = yellowBrush;
            statusIcon = "\uE769"; // Pause
            statusText = "Monitoring Paused";
            PortText.Visibility = Visibility.Collapsed;

            // Show admin paused message
            AdminPausedPanel.Visibility = Visibility.Visible;
            if (!string.IsNullOrEmpty(remote.ItSupport))
            {
                ItSupportText.Text = $"Contact: {remote.ItSupport}";
                ItSupportText.Visibility = Visibility.Visible;
            }
            else
            {
                ItSupportText.Visibility = Visibility.Collapsed;
            }
        }
        else if (remote.ProxyActive)
        {
            // Monitoring Active - Green
            statusColor = successBrush;
            statusIcon = "\uEA18"; // Shield with checkmark
            statusText = "Monitoring Active";
            AdminPausedPanel.Visibility = Visibility.Collapsed;

            // Show port info
            if (App.MitmService.CurrentPort.HasValue)
            {
                PortText.Text = $"Port {App.MitmService.CurrentPort.Value}";
                PortText.Visibility = Visibility.Visible;
            }
        }
        else if (!isCertInstalled)
        {
            // Setup Required - Gray
            statusColor = grayBrush;
            statusIcon = "\uEAFC"; // Shield slash
            statusText = "Setup Required";
            PortText.Visibility = Visibility.Collapsed;
            AdminPausedPanel.Visibility = Visibility.Collapsed;
        }
        else if (status == ConnectionStatus.Error)
        {
            // Error - Red
            statusColor = errorBrush;
            statusIcon = "\uEA39"; // Shield error
            statusText = "Error";
            PortText.Visibility = Visibility.Collapsed;
            AdminPausedPanel.Visibility = Visibility.Collapsed;
        }
        else
        {
            // Starting... - Orange (sensor enabled but proxy not yet active)
            statusColor = warningBrush;
            statusIcon = "\uE916"; // Progress ring / sync
            statusText = "Starting...";
            PortText.Visibility = Visibility.Collapsed;
            AdminPausedPanel.Visibility = Visibility.Collapsed;
        }

        StatusCircle.Fill = statusColor;
        StatusIcon.Text = statusIcon;
        StatusIcon.Foreground = statusColor;
        StatusText.Text = statusText;
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        SettingsWindow.ShowInstance();
    }

    private async void RetryButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;
            AppState.Instance.ErrorMessage = string.Empty;
            ErrorPanel.Visibility = Visibility.Collapsed;

            // Restart mitmproxy - addon will handle proxy configuration
            await App.MitmService.RestartAsync();
        }
        catch (Exception ex)
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = ex.Message;
        }
    }

    private void OnUpdateStatusChanged(object? sender, EventArgs e)
    {
        Dispatcher.BeginInvoke(UpdateUpdateBanner);
    }

    private void UpdateUpdateBanner()
    {
        var svc = UpdateCheckService.Instance;
        if (!svc.UpdateAvailable)
        {
            UpdateBanner.Visibility = Visibility.Collapsed;
            return;
        }

        UpdateBanner.Visibility = Visibility.Visible;

        if (svc.Unsupported)
        {
            UpdateText.Text = "Update required";
            UpdateIcon.Text = "\uE7BA"; // Warning triangle
            var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;
            UpdateBanner.Background = errorBrush;
            UpdateButton.Foreground = errorBrush;
        }
        else
        {
            UpdateText.Text = $"v{svc.LatestVersion} available";
            UpdateIcon.Text = "\uE74A"; // Up arrow
        }
    }

    private void UpdateButton_Click(object sender, RoutedEventArgs e)
    {
        var url = UpdateCheckService.Instance.DownloadUrl;
        if (!string.IsNullOrEmpty(url))
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
    }
}
