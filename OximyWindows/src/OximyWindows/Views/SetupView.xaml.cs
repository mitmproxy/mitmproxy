using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using OximyWindows.Core;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Setup view for certificate installation.
/// Proxy configuration is now handled automatically by the Python addon.
/// </summary>
public partial class SetupView : UserControl
{
    private bool _isCertificateInstalled;
    private bool _isProcessing;

    public SetupView()
    {
        InitializeComponent();
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
    /// Update button states based on completion.
    /// </summary>
    private void UpdateButtonStates()
    {
        // Continue button is enabled when certificate is installed
        StartButton.IsEnabled = _isCertificateInstalled && !_isProcessing;
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
    /// Uses automatic installation with UAC elevation prompt.
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
            // Try automatic installation with elevation (shows UAC prompt)
            var success = await App.CertificateService.InstallCAAutomaticallyAsync();

            if (success)
            {
                MarkCertificateComplete();
                Debug.WriteLine("[SetupView] Certificate installed automatically via UAC");
            }
            else
            {
                ShowError("Certificate installation was cancelled. Please try again.");
                CertificateArrow.Visibility = Visibility.Visible;
                Debug.WriteLine("[SetupView] Certificate installation cancelled by user");
            }
        }
        catch (Exception ex)
        {
            ShowError($"Failed to install certificate: {ex.Message}");
            CertificateArrow.Visibility = Visibility.Visible;
            Debug.WriteLine($"[SetupView] Certificate error: {ex.Message}");
        }
        finally
        {
            _isProcessing = false;
            CertificateLoading.Visibility = Visibility.Collapsed;
            UpdateButtonStates();
        }
    }

    /// <summary>
    /// Handle continue button click.
    /// Completes setup and transitions to Connected phase.
    /// MitmService will be started automatically and the addon will enable the proxy.
    /// </summary>
    private void OnStartMonitoringClick(object sender, RoutedEventArgs e)
    {
        if (!_isCertificateInstalled)
            return;

        // Complete setup and transition to Connected phase
        AppState.Instance.CompleteSetup();

        // Start mitmproxy - the addon will handle proxy configuration
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
