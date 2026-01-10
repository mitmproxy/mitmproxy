using System.Windows;
using System.Windows.Controls;
using OximyWindows.Core;
using OximyWindows.Services;

namespace OximyWindows.Views;

public partial class PermissionsView : UserControl
{
    private bool _isCertInstalled;
    private bool _isProxyEnabled;

    public PermissionsView()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        // Check current status
        UpdateStatus();
    }

    private void UpdateStatus()
    {
        _isCertInstalled = App.CertificateService.IsCAInstalled;
        _isProxyEnabled = App.ProxyService.IsProxyEnabled;

        // Update Certificate UI
        if (_isCertInstalled)
        {
            CertCheckmark.Visibility = Visibility.Visible;
            CertEmpty.Visibility = Visibility.Collapsed;
            CertProgress.Visibility = Visibility.Collapsed;
            CertGrantButton.Visibility = Visibility.Collapsed;
        }
        else
        {
            CertCheckmark.Visibility = Visibility.Collapsed;
            CertEmpty.Visibility = Visibility.Visible;
            CertProgress.Visibility = Visibility.Collapsed;
            CertGrantButton.Visibility = Visibility.Visible;
        }

        // Update Proxy UI
        ProxyGrantButton.IsEnabled = _isCertInstalled;

        if (_isProxyEnabled)
        {
            ProxyCheckmark.Visibility = Visibility.Visible;
            ProxyEmpty.Visibility = Visibility.Collapsed;
            ProxyProgress.Visibility = Visibility.Collapsed;
            ProxyGrantButton.Visibility = Visibility.Collapsed;
        }
        else
        {
            ProxyCheckmark.Visibility = Visibility.Collapsed;
            ProxyEmpty.Visibility = Visibility.Visible;
            ProxyProgress.Visibility = Visibility.Collapsed;
            ProxyGrantButton.Visibility = Visibility.Visible;
        }

        // Update Continue button
        ContinueButton.IsEnabled = _isCertInstalled && _isProxyEnabled;
    }

    private async void CertGrantButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            // Show progress
            CertProgress.Visibility = Visibility.Visible;
            CertEmpty.Visibility = Visibility.Collapsed;
            CertGrantButton.IsEnabled = false;
            ErrorText.Visibility = Visibility.Collapsed;

            // Generate and install certificate
            await App.CertificateService.GenerateCAAsync();
            await App.CertificateService.InstallCAAsync();

            App.CertificateService.CheckStatus();
            UpdateStatus();
        }
        catch (CertificateException ex)
        {
            ShowError(ex.Message);
            CertProgress.Visibility = Visibility.Collapsed;
            CertEmpty.Visibility = Visibility.Visible;
            CertGrantButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            ShowError($"Failed to install certificate: {ex.Message}");
            CertProgress.Visibility = Visibility.Collapsed;
            CertEmpty.Visibility = Visibility.Visible;
            CertGrantButton.IsEnabled = true;
        }
    }

    private async void ProxyGrantButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            // Show progress
            ProxyProgress.Visibility = Visibility.Visible;
            ProxyEmpty.Visibility = Visibility.Collapsed;
            ProxyGrantButton.IsEnabled = false;
            ErrorText.Visibility = Visibility.Collapsed;

            // Start mitmproxy first to get the port
            await App.MitmService.StartAsync();

            if (!App.MitmService.CurrentPort.HasValue)
            {
                throw new Exception("Failed to start proxy service");
            }

            // Enable system proxy
            App.ProxyService.EnableProxy(App.MitmService.CurrentPort.Value);

            App.ProxyService.CheckStatus();
            UpdateStatus();
        }
        catch (ProxyException ex)
        {
            ShowError(ex.Message);
            ProxyProgress.Visibility = Visibility.Collapsed;
            ProxyEmpty.Visibility = Visibility.Visible;
            ProxyGrantButton.IsEnabled = true;
        }
        catch (MitmException ex)
        {
            ShowError(ex.Message);
            ProxyProgress.Visibility = Visibility.Collapsed;
            ProxyEmpty.Visibility = Visibility.Visible;
            ProxyGrantButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            ShowError($"Failed to enable proxy: {ex.Message}");
            ProxyProgress.Visibility = Visibility.Collapsed;
            ProxyEmpty.Visibility = Visibility.Visible;
            ProxyGrantButton.IsEnabled = true;
        }
    }

    private void ContinueButton_Click(object sender, RoutedEventArgs e)
    {
        AppState.Instance.CompletePermissions();
    }

    private void ShowError(string message)
    {
        ErrorText.Text = message;
        ErrorText.Visibility = Visibility.Visible;
    }
}
