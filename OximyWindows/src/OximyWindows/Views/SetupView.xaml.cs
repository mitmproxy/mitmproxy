using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using OximyWindows.Core;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Setup view for certificate installation and proxy configuration.
/// Matches the Mac app's SetupView functionality.
/// </summary>
public partial class SetupView : UserControl
{
    private bool _isCertificateInstalled;
    private bool _isProxyConfigured;
    private bool _isProcessing;

    public SetupView()
    {
        InitializeComponent();

        // Check current status
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        // Check if certificate is already installed
        App.CertificateService.CheckStatus();
        if (App.CertificateService.IsCAInstalled)
        {
            MarkCertificateComplete();
        }

        // Check if proxy is configured
        App.ProxyService.CheckStatus();
        if (App.ProxyService.IsProxyEnabled)
        {
            MarkProxyComplete();
        }

        UpdateButtonStates();
    }

    /// <summary>
    /// Mark certificate step as complete.
    /// </summary>
    private void MarkCertificateComplete()
    {
        _isCertificateInstalled = true;
        CertificateStepBorder.Background = new SolidColorBrush(Color.FromRgb(0x4C, 0xAF, 0x50));
        CertificateStepText.Text = "\u2713"; // Checkmark
        CertificateArrow.Visibility = Visibility.Collapsed;
        CertificateButton.IsEnabled = false;
        CertificateButton.Opacity = 0.7;

        AppState.Instance.IsSetupCertificateComplete = true;
    }

    /// <summary>
    /// Mark proxy step as complete.
    /// </summary>
    private void MarkProxyComplete()
    {
        _isProxyConfigured = true;
        ProxyStepBorder.Background = new SolidColorBrush(Color.FromRgb(0x4C, 0xAF, 0x50));
        ProxyStepText.Text = "\u2713"; // Checkmark
        ProxyArrow.Visibility = Visibility.Collapsed;
        ProxyButton.IsEnabled = false;
        ProxyButton.Opacity = 0.7;

        AppState.Instance.IsSetupProxyComplete = true;
    }

    /// <summary>
    /// Update button states based on completion.
    /// </summary>
    private void UpdateButtonStates()
    {
        // Proxy button is enabled only after certificate is installed
        ProxyButton.IsEnabled = _isCertificateInstalled && !_isProxyConfigured && !_isProcessing;

        // Start button is enabled only when both steps are complete
        StartButton.IsEnabled = _isCertificateInstalled && _isProxyConfigured && !_isProcessing;
    }

    /// <summary>
    /// Show error message.
    /// </summary>
    private void ShowError(string message)
    {
        ErrorText.Text = message;
        ErrorText.Visibility = Visibility.Visible;
    }

    /// <summary>
    /// Clear error message.
    /// </summary>
    private void ClearError()
    {
        ErrorText.Text = string.Empty;
        ErrorText.Visibility = Visibility.Collapsed;
    }

    /// <summary>
    /// Handle install certificate click.
    /// </summary>
    private async void OnInstallCertificateClick(object sender, RoutedEventArgs e)
    {
        if (_isProcessing || _isCertificateInstalled)
            return;

        _isProcessing = true;
        ClearError();
        CertificateArrow.Visibility = Visibility.Collapsed;
        CertificateLoading.Visibility = Visibility.Visible;

        try
        {
            // Generate and install certificate
            await App.CertificateService.InstallCAAsync();

            MarkCertificateComplete();
            Debug.WriteLine("[SetupView] Certificate installed successfully");
        }
        catch (CertificateException ex)
        {
            ShowError($"Certificate installation failed: {ex.Message}");
            CertificateArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Certificate error: {ex.Message}");
        }
        catch (Exception ex)
        {
            ShowError("Failed to install certificate. Please try again.");
            CertificateArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Unexpected error: {ex.Message}");
        }
        finally
        {
            _isProcessing = false;
            CertificateLoading.Visibility = Visibility.Collapsed;
            UpdateButtonStates();
        }
    }

    /// <summary>
    /// Handle enable proxy click.
    /// </summary>
    private async void OnEnableProxyClick(object sender, RoutedEventArgs e)
    {
        if (_isProcessing || _isProxyConfigured || !_isCertificateInstalled)
            return;

        _isProcessing = true;
        ClearError();
        ProxyArrow.Visibility = Visibility.Collapsed;
        ProxyLoading.Visibility = Visibility.Visible;

        try
        {
            // Start mitmproxy first
            await App.MitmService.StartAsync();

            // Then enable system proxy
            var port = App.MitmService.CurrentPort ?? Constants.PreferredPort;
            App.ProxyService.EnableProxy(port);

            MarkProxyComplete();
            Debug.WriteLine($"[SetupView] Proxy enabled on port {port}");
        }
        catch (MitmException ex)
        {
            ShowError($"Failed to start proxy: {ex.Message}");
            ProxyArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Mitm error: {ex.Message}");
        }
        catch (ProxyException ex)
        {
            ShowError($"Failed to configure proxy: {ex.Message}");
            ProxyArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Proxy error: {ex.Message}");
        }
        catch (Exception ex)
        {
            ShowError("Failed to configure proxy. Please try again.");
            ProxyArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Unexpected error: {ex.Message}");
        }
        finally
        {
            _isProcessing = false;
            ProxyLoading.Visibility = Visibility.Collapsed;
            UpdateButtonStates();
        }
    }

    /// <summary>
    /// Handle start monitoring click.
    /// </summary>
    private void OnStartMonitoringClick(object sender, RoutedEventArgs e)
    {
        if (!_isCertificateInstalled || !_isProxyConfigured)
            return;

        // Complete setup and transition to Connected phase
        AppState.Instance.CompleteSetup();

        // Start services if not already running
        if (!App.MitmService.IsRunning)
        {
            _ = App.MitmService.StartAsync();
        }

        // Start heartbeat and sync services
        HeartbeatService.Instance.Start();
        SyncService.Instance.Start();

        Debug.WriteLine("[SetupView] Setup complete, transitioning to Connected phase");
    }

    /// <summary>
    /// Handle skip click.
    /// </summary>
    private void OnSkipClick(object sender, RoutedEventArgs e)
    {
        // Skip setup and go directly to Connected phase
        // User can set up later from settings
        AppState.Instance.SkipSetup();

        Debug.WriteLine("[SetupView] Setup skipped");
    }
}
