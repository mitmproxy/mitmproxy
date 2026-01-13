using System.Diagnostics;
using System.Drawing;
using System.Windows;
using System.Windows.Input;
using Hardcodet.Wpf.TaskbarNotification;
using OximyWindows.Core;
using OximyWindows.ViewModels;

namespace OximyWindows.Views;

public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;
    private TrayPopup? _popup;

    public MainWindow()
    {
        InitializeComponent();

        _viewModel = new MainViewModel();
        DataContext = _viewModel;

        // Set up tray icon
        SetupTrayIcon();

        // Subscribe to state changes
        AppState.Instance.PropertyChanged += OnAppStateChanged;

        // Subscribe to network changes
        App.NetworkMonitorService.NetworkChanged += OnNetworkChanged;
        App.NetworkMonitorService.StartMonitoring();

        // Subscribe to mitmproxy events
        App.MitmService.MaxRestartsExceeded += OnMitmMaxRestartsExceeded;

        // Show popup on first launch or if not connected
        if (AppState.Instance.Phase != Phase.Connected)
        {
            ShowPopup();
        }

        // Auto-start mitmproxy if we're in Connected phase
        if (AppState.Instance.Phase == Phase.Connected)
        {
            _ = StartServicesAsync();
        }
    }

    private void SetupTrayIcon()
    {
        // Create icon from file or use default
        try
        {
            // Try multiple possible locations
            var possiblePaths = new[]
            {
                System.IO.Path.Combine(AppContext.BaseDirectory, "oximy.ico"),
                System.IO.Path.Combine(AppContext.BaseDirectory, "Assets", "oximy.ico"),
            };

            foreach (var iconPath in possiblePaths)
            {
                if (System.IO.File.Exists(iconPath))
                {
                    TrayIcon.Icon = new Icon(iconPath);
                    Debug.WriteLine($"Loaded tray icon from: {iconPath}");
                    break;
                }
            }

            // Fallback to system icon if no custom icon found
            TrayIcon.Icon ??= SystemIcons.Application;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Failed to load tray icon: {ex.Message}");
            TrayIcon.Icon = SystemIcons.Application;
        }

        // Update tooltip based on status
        UpdateTrayTooltip();
    }

    private void UpdateTrayTooltip()
    {
        var status = AppState.Instance.ConnectionStatus switch
        {
            ConnectionStatus.Connected => "Connected",
            ConnectionStatus.Connecting => "Connecting...",
            ConnectionStatus.Error => "Error",
            _ => "Disconnected"
        };

        TrayIcon.ToolTipText = $"Oximy - {status}";
    }

    private void OnAppStateChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(AppState.ConnectionStatus))
        {
            Dispatcher.Invoke(UpdateTrayTooltip);
        }
        else if (e.PropertyName == nameof(AppState.Phase))
        {
            Dispatcher.Invoke(() =>
            {
                // Refresh the popup to show the new phase's view
                if (_popup != null)
                {
                    _popup.RefreshContent();
                }
                else
                {
                    ShowPopup();
                }
            });
        }
    }

    private async void OnNetworkChanged(object? sender, EventArgs e)
    {
        Debug.WriteLine("Network changed, reconfiguring proxy...");

        if (AppState.Instance.Phase == Phase.Connected && App.MitmService.IsRunning)
        {
            var port = App.MitmService.CurrentPort;
            if (port.HasValue && App.ProxyService.IsProxyEnabled)
            {
                // Update proxy configuration for new network
                App.ProxyService.UpdatePort(port.Value);
            }
        }
    }

    private void OnMitmMaxRestartsExceeded(object? sender, EventArgs e)
    {
        Dispatcher.Invoke(() =>
        {
            TrayIcon.ShowBalloonTip(
                "Oximy Error",
                "mitmproxy crashed too many times. Click to restart.",
                BalloonIcon.Error);

            ShowPopup();
        });
    }

    private async Task StartServicesAsync()
    {
        try
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;

            // Start mitmproxy
            await App.MitmService.StartAsync();

            // Enable proxy
            if (App.MitmService.CurrentPort.HasValue)
            {
                App.ProxyService.EnableProxy(App.MitmService.CurrentPort.Value);
            }

            AppState.Instance.ConnectionStatus = ConnectionStatus.Connected;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Failed to start services: {ex.Message}");
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = ex.Message;
        }
    }

    public void ShowPopup()
    {
        if (_popup == null)
        {
            _popup = new TrayPopup();
            _popup.Closed += (s, e) => _popup = null;
        }

        _popup.ShowNearTray(TrayIcon);
    }

    public void HidePopup()
    {
        _popup?.Hide();
    }

    public void TogglePopup()
    {
        if (_popup?.IsVisible == true)
            HidePopup();
        else
            ShowPopup();
    }

    protected override void OnClosed(EventArgs e)
    {
        // Clean up
        TrayIcon.Dispose();
        App.NetworkMonitorService.StopMonitoring();

        base.OnClosed(e);
    }
}
