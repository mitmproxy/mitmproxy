using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class StatusView : UserControl
{
    private readonly DispatcherTimer _refreshTimer;
    private bool _isToggling;

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
        App.MitmService.Started += OnMitmStarted;
        App.MitmService.Stopped += OnMitmStopped;
    }

    private void UnsubscribeFromEvents()
    {
        AppState.Instance.PropertyChanged -= OnAppStateChanged;
        App.MitmService.Started -= OnMitmStarted;
        App.MitmService.Stopped -= OnMitmStopped;
    }

    private void OnMitmStarted(object? sender, EventArgs e) => Dispatcher.Invoke(UpdateUI);
    private void OnMitmStopped(object? sender, EventArgs e) => Dispatcher.Invoke(UpdateUI);
    private void OnRefreshTimerTick(object? sender, EventArgs e) => AppState.Instance.RefreshEventsCount();

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        SubscribeToEvents();
        UpdateUI();
        _refreshTimer.Start();
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        _refreshTimer.Stop();
        UnsubscribeFromEvents();
    }

    private void OnAppStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        Dispatcher.Invoke(UpdateUI);
    }

    private void UpdateUI()
    {
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

        // Update certificate warning
        App.CertificateService.CheckStatus();
        CertWarningText.Visibility = App.CertificateService.IsCAInstalled ? Visibility.Collapsed : Visibility.Visible;

        // Update capture button
        UpdateCaptureButton();
    }

    private void UpdateStatusUI()
    {
        var successBrush = TryFindResource("SuccessBrush") as SolidColorBrush ?? Brushes.Green;
        var warningBrush = TryFindResource("WarningBrush") as SolidColorBrush ?? Brushes.Orange;
        var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;
        var grayBrush = TryFindResource("TextSecondaryBrush") as SolidColorBrush ?? Brushes.Gray;

        var isRunning = App.MitmService.IsRunning;
        var isCertInstalled = App.CertificateService.IsCAInstalled;
        var status = AppState.Instance.ConnectionStatus;

        // Determine status color and icon based on state (like Mac)
        SolidColorBrush statusColor;
        string statusIcon;
        string statusText;

        if (isRunning && status == ConnectionStatus.Connected)
        {
            // Monitoring Active - Green
            statusColor = successBrush;
            statusIcon = "\uEA18"; // Shield with checkmark
            statusText = "Monitoring Active";

            // Show port info
            if (App.MitmService.CurrentPort.HasValue)
            {
                PortText.Text = $"Port {App.MitmService.CurrentPort.Value}";
                PortText.Visibility = Visibility.Visible;
            }
        }
        else if (status == ConnectionStatus.Connecting)
        {
            // Starting - Orange
            statusColor = warningBrush;
            statusIcon = "\uE916"; // Progress ring
            statusText = "Starting...";
            PortText.Visibility = Visibility.Collapsed;
        }
        else if (status == ConnectionStatus.Error)
        {
            // Error - Red
            statusColor = errorBrush;
            statusIcon = "\uEA39"; // Shield error
            statusText = "Error";
            PortText.Visibility = Visibility.Collapsed;
        }
        else if (!isCertInstalled)
        {
            // Setup Required - Gray
            statusColor = grayBrush;
            statusIcon = "\uEAFC"; // Shield slash
            statusText = "Setup Required";
            PortText.Visibility = Visibility.Collapsed;
        }
        else
        {
            // Monitoring Paused - Orange
            statusColor = warningBrush;
            statusIcon = "\uEA18"; // Shield
            statusText = "Monitoring Paused";
            PortText.Visibility = Visibility.Collapsed;
        }

        StatusCircle.Fill = statusColor;
        StatusIcon.Text = statusIcon;
        StatusIcon.Foreground = statusColor;
        StatusText.Text = statusText;
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var settingsWindow = new SettingsWindow();
        settingsWindow.Show();
    }

    private async void RetryButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;
            AppState.Instance.ErrorMessage = string.Empty;
            ErrorPanel.Visibility = Visibility.Collapsed;

            // Restart mitmproxy
            await App.MitmService.RestartAsync();

            // Re-enable proxy
            if (App.MitmService.CurrentPort.HasValue)
            {
                App.ProxyService.EnableProxy(App.MitmService.CurrentPort.Value);
            }
        }
        catch (Exception ex)
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = ex.Message;
        }
    }

    private async void CaptureToggleButton_Click(object sender, RoutedEventArgs e)
    {
        if (_isToggling) return;
        _isToggling = true;
        CaptureToggleButton.IsEnabled = false;

        try
        {
            if (App.MitmService.IsRunning)
            {
                // Stop monitoring
                App.ProxyService.DisableProxy();
                App.MitmService.Stop();
                AppState.Instance.ConnectionStatus = ConnectionStatus.Disconnected;
            }
            else
            {
                // Verify certificate is installed first
                App.CertificateService.CheckStatus();
                if (!App.CertificateService.IsCAInstalled)
                {
                    MessageBox.Show(
                        "Please install the CA certificate first.\n\nGo to Settings to install the certificate.",
                        "Certificate Required",
                        MessageBoxButton.OK,
                        MessageBoxImage.Warning);
                    return;
                }

                // Start monitoring
                AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;
                await App.MitmService.StartAsync();

                if (App.MitmService.CurrentPort.HasValue)
                {
                    App.ProxyService.EnableProxy(App.MitmService.CurrentPort.Value);
                }
            }
        }
        catch (Exception ex)
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = ex.Message;
        }
        finally
        {
            _isToggling = false;
            CaptureToggleButton.IsEnabled = true;
            UpdateUI();
        }
    }

    private void UpdateCaptureButton()
    {
        var isRunning = App.MitmService.IsRunning;
        var isCertInstalled = App.CertificateService.IsCAInstalled;

        // Update icon and text
        CaptureButtonIcon.Text = isRunning ? "\uE71A" : "\uE768"; // Stop : Play
        CaptureButtonText.Text = isRunning ? "Stop Monitoring" : "Start Monitoring";

        // Update button color (orange when running, accent when stopped)
        var accentBrush = TryFindResource("AccentBrush") as SolidColorBrush ?? Brushes.Blue;
        var warningBrush = TryFindResource("WarningBrush") as SolidColorBrush ?? Brushes.Orange;
        CaptureToggleButton.Background = isRunning ? warningBrush : accentBrush;

        // Disable button if certificate not installed
        CaptureToggleButton.IsEnabled = isCertInstalled || isRunning;
    }
}
