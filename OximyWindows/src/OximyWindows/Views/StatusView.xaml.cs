using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class StatusView : UserControl
{
    private readonly DispatcherTimer _refreshTimer;

    public StatusView()
    {
        InitializeComponent();

        // Set up refresh timer for events count
        _refreshTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(5)
        };
        _refreshTimer.Tick += (s, e) => RefreshEventsCount();

        Loaded += OnLoaded;
        Unloaded += OnUnloaded;

        // Subscribe to state changes
        AppState.Instance.PropertyChanged += OnAppStateChanged;
        App.NetworkMonitorService.PropertyChanged += OnNetworkChanged;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        UpdateUI();
        _refreshTimer.Start();
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        _refreshTimer.Stop();
    }

    private void OnAppStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        Dispatcher.Invoke(UpdateUI);
    }

    private void OnNetworkChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        Dispatcher.Invoke(UpdateNetworkUI);
    }

    private void UpdateUI()
    {
        var state = AppState.Instance;

        // Update status
        UpdateStatusUI(state.ConnectionStatus);

        // Update device info
        DeviceText.Text = state.DeviceName;
        WorkspaceText.Text = state.WorkspaceName;

        // Update stats
        EventsCountText.Text = state.EventsCapturedToday.ToString();

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

        // Update version
        VersionText.Text = $"Oximy v{Constants.Version}";

        // Update network
        UpdateNetworkUI();
    }

    private void UpdateStatusUI(ConnectionStatus status)
    {
        var successBrush = TryFindResource("SuccessBrush") as SolidColorBrush ?? Brushes.Green;
        var warningBrush = TryFindResource("WarningBrush") as SolidColorBrush ?? Brushes.Orange;
        var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;
        var borderBrush = TryFindResource("BorderBrush") as SolidColorBrush ?? Brushes.Gray;

        switch (status)
        {
            case ConnectionStatus.Connected:
                StatusText.Text = "Connected";
                StatusDot.Fill = successBrush;
                StatusCircle.Fill = successBrush;
                break;

            case ConnectionStatus.Connecting:
                StatusText.Text = "Connecting...";
                StatusDot.Fill = warningBrush;
                StatusCircle.Fill = warningBrush;
                break;

            case ConnectionStatus.Error:
                StatusText.Text = "Error";
                StatusDot.Fill = errorBrush;
                StatusCircle.Fill = errorBrush;
                break;

            default:
                StatusText.Text = "Disconnected";
                StatusDot.Fill = borderBrush;
                StatusCircle.Fill = borderBrush;
                break;
        }
    }

    private void UpdateNetworkUI()
    {
        var networkMonitor = App.NetworkMonitorService;
        NetworkText.Text = networkMonitor.NetworkDescription;

        var successBrush = TryFindResource("SuccessBrush") as SolidColorBrush ?? Brushes.Green;
        var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;

        NetworkIndicator.Fill = networkMonitor.IsConnected ? successBrush : errorBrush;
    }

    private void RefreshEventsCount()
    {
        AppState.Instance.RefreshEventsCount();
        EventsCountText.Text = AppState.Instance.EventsCapturedToday.ToString();
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
}
