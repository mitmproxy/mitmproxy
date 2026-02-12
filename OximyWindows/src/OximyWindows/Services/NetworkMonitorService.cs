using System.ComponentModel;
using System.Net.NetworkInformation;
using System.Runtime.CompilerServices;

namespace OximyWindows.Services;

/// <summary>
/// Monitors network interface changes and notifies when proxy reconfiguration may be needed.
/// Uses debouncing to avoid rapid reconfiguration on network transitions.
/// </summary>
public class NetworkMonitorService : INotifyPropertyChanged, IDisposable
{
    private CancellationTokenSource? _debounceCts;
    private readonly TimeSpan _debounceInterval = TimeSpan.FromSeconds(1);
    private bool _isMonitoring;
    private bool _disposed;

    public event EventHandler? NetworkChanged;

    private bool _isConnected;
    public bool IsConnected
    {
        get => _isConnected;
        private set => SetProperty(ref _isConnected, value);
    }

    private string _networkDescription = "Unknown";
    public string NetworkDescription
    {
        get => _networkDescription;
        private set => SetProperty(ref _networkDescription, value);
    }

    /// <summary>
    /// Start monitoring network changes.
    /// </summary>
    public void StartMonitoring()
    {
        if (_isMonitoring)
            return;

        NetworkChange.NetworkAddressChanged += OnNetworkAddressChanged;
        NetworkChange.NetworkAvailabilityChanged += OnNetworkAvailabilityChanged;

        _isMonitoring = true;

        // Initial status check
        UpdateNetworkStatus();
    }

    /// <summary>
    /// Stop monitoring network changes.
    /// </summary>
    public void StopMonitoring()
    {
        if (!_isMonitoring)
            return;

        NetworkChange.NetworkAddressChanged -= OnNetworkAddressChanged;
        NetworkChange.NetworkAvailabilityChanged -= OnNetworkAvailabilityChanged;

        _debounceCts?.Cancel();
        _isMonitoring = false;
    }

    private void OnNetworkAddressChanged(object? sender, EventArgs e)
    {
        ScheduleNetworkUpdate();
    }

    private void OnNetworkAvailabilityChanged(object? sender, NetworkAvailabilityEventArgs e)
    {
        ScheduleNetworkUpdate();
    }

    /// <summary>
    /// Schedule a network status update with debouncing.
    /// </summary>
    private async void ScheduleNetworkUpdate()
    {
        // Cancel any pending update
        _debounceCts?.Cancel();
        _debounceCts = new CancellationTokenSource();

        try
        {
            await Task.Delay(_debounceInterval, _debounceCts.Token);

            var wasConnected = IsConnected;
            UpdateNetworkStatus();

            // Log connectivity transitions
            if (wasConnected && !IsConnected)
            {
                OximyLogger.Log(EventCode.NET_STATE_102, "Connectivity lost");
                OximyLogger.SetTag("network_connected", "false");
            }
            else if (!wasConnected && IsConnected)
            {
                OximyLogger.Log(EventCode.NET_STATE_103, "Connectivity restored",
                    new Dictionary<string, object> { ["network_type"] = NetworkDescription });
                OximyLogger.SetTag("network_connected", "true");
                OximyLogger.SetTag("network_type", NetworkDescription);
            }

            NetworkChanged?.Invoke(this, EventArgs.Empty);
        }
        catch (TaskCanceledException)
        {
            // Debounced - another change came in before we could process
        }
    }

    /// <summary>
    /// Update network status information.
    /// </summary>
    private void UpdateNetworkStatus()
    {
        IsConnected = NetworkInterface.GetIsNetworkAvailable();

        if (!IsConnected)
        {
            NetworkDescription = "No Connection";
            return;
        }

        // Find active interface type
        var interfaces = NetworkInterface.GetAllNetworkInterfaces()
            .Where(ni => ni.OperationalStatus == OperationalStatus.Up &&
                        ni.NetworkInterfaceType != NetworkInterfaceType.Loopback)
            .ToList();

        if (interfaces.Any(ni => ni.NetworkInterfaceType == NetworkInterfaceType.Wireless80211))
        {
            NetworkDescription = "Wi-Fi";
        }
        else if (interfaces.Any(ni => ni.NetworkInterfaceType == NetworkInterfaceType.Ethernet))
        {
            NetworkDescription = "Ethernet";
        }
        else if (interfaces.Any(ni => ni.NetworkInterfaceType == NetworkInterfaceType.Ppp))
        {
            NetworkDescription = "VPN";
        }
        else if (interfaces.Any())
        {
            NetworkDescription = "Connected";
        }
        else
        {
            NetworkDescription = "Unknown";
        }
    }

    /// <summary>
    /// Get list of active network interface names.
    /// </summary>
    public IReadOnlyList<string> GetActiveInterfaces()
    {
        return NetworkInterface.GetAllNetworkInterfaces()
            .Where(ni => ni.OperationalStatus == OperationalStatus.Up &&
                        ni.NetworkInterfaceType != NetworkInterfaceType.Loopback)
            .Select(ni => ni.Name)
            .ToList();
    }

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        StopMonitoring();
        _debounceCts?.Dispose();
    }

    #region INotifyPropertyChanged

    public event PropertyChangedEventHandler? PropertyChanged;

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    #endregion
}
