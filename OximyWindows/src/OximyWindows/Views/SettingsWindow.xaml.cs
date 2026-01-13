using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Media;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class SettingsWindow : Window
{
    public SettingsWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        VersionText.Text = $"Version {Constants.Version}";
        WorkspaceText.Text = AppState.Instance.WorkspaceName;
        StartupToggle.IsChecked = App.StartupService.IsEnabled;
        UpdateCertificateUI();
    }

    private void UpdateCertificateUI()
    {
        App.CertificateService.CheckStatus();

        var successBrush = TryFindResource("SuccessBrush") as SolidColorBrush ?? Brushes.Green;
        var warningBrush = TryFindResource("WarningBrush") as SolidColorBrush ?? Brushes.Orange;
        var errorBrush = TryFindResource("ErrorBrush") as SolidColorBrush ?? Brushes.Red;

        if (App.CertificateService.IsCAInstalled)
        {
            CertStatusText.Text = "Installed and trusted";
            CertStatusIndicator.Fill = successBrush;
            GenerateCertText.Text = "Regenerate Certificate";
            InstallCertText.Text = "Reinstall Certificate";
            UninstallCertButton.Visibility = Visibility.Visible;
        }
        else if (App.CertificateService.IsCAGenerated)
        {
            CertStatusText.Text = "Generated but not installed";
            CertStatusIndicator.Fill = warningBrush;
            GenerateCertText.Text = "Regenerate Certificate";
            InstallCertText.Text = "Install Certificate";
            UninstallCertButton.Visibility = Visibility.Collapsed;
        }
        else
        {
            CertStatusText.Text = "Not generated";
            CertStatusIndicator.Fill = errorBrush;
            GenerateCertText.Text = "Generate Certificate";
            InstallCertText.Text = "Install Certificate";
            InstallCertButton.IsEnabled = false;
            UninstallCertButton.Visibility = Visibility.Collapsed;
        }
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }

    private async void CheckUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            CheckUpdateButton.IsEnabled = false;
            CheckUpdateButton.Content = "Checking...";
            UpdateStatusText.Text = "Checking for updates...";
            UpdateProgressBar.Visibility = Visibility.Collapsed;

            var updateAvailable = await Services.UpdateService.Instance.CheckForUpdatesAsync();

            if (updateAvailable)
            {
                var latestVersion = Services.UpdateService.Instance.LatestVersion;
                UpdateStatusText.Text = $"Update available: v{latestVersion}";
                CheckUpdateButton.Content = "Download & Install";

                // Change button behavior to download update
                CheckUpdateButton.Click -= CheckUpdateButton_Click;
                CheckUpdateButton.Click += DownloadUpdateButton_Click;
            }
            else
            {
                UpdateStatusText.Text = "You're up to date!";
                CheckUpdateButton.Content = "Check for Updates";
            }
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = $"Error: {ex.Message}";
            CheckUpdateButton.Content = "Check for Updates";
        }
        finally
        {
            CheckUpdateButton.IsEnabled = true;
        }
    }

    private async void DownloadUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            CheckUpdateButton.IsEnabled = false;
            CheckUpdateButton.Content = "Downloading...";
            UpdateProgressBar.Visibility = Visibility.Visible;
            UpdateProgressBar.Value = 0;

            // Subscribe to progress updates
            Services.UpdateService.Instance.PropertyChanged += (s, args) =>
            {
                if (args.PropertyName == nameof(Services.UpdateService.DownloadProgress))
                {
                    Dispatcher.Invoke(() =>
                    {
                        UpdateProgressBar.Value = Services.UpdateService.Instance.DownloadProgress;
                        UpdateStatusText.Text = $"Downloading... {Services.UpdateService.Instance.DownloadProgress}%";
                    });
                }
            };

            await Services.UpdateService.Instance.DownloadAndApplyUpdateAsync();
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = $"Download failed: {ex.Message}";
            CheckUpdateButton.Content = "Retry Download";
            UpdateProgressBar.Visibility = Visibility.Collapsed;
            CheckUpdateButton.IsEnabled = true;
        }
    }

    private void HelpButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.HelpUrl);
    }

    private void FeedbackButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.FeedbackUrl);
    }

    private void OpenLogsButton_Click(object sender, RoutedEventArgs e)
    {
        OpenFolder(Constants.LogsDir);
    }

    private void OpenTracesButton_Click(object sender, RoutedEventArgs e)
    {
        OpenFolder(Constants.TracesDir);
    }

    private void StartupToggle_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            App.StartupService.Toggle();
            StartupToggle.IsChecked = App.StartupService.IsEnabled;
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Failed to change startup setting: {ex.Message}",
                "Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            StartupToggle.IsChecked = App.StartupService.IsEnabled;
        }
    }

    private void TermsButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.TermsUrl);
    }

    private void PrivacyButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.PrivacyUrl);
    }

    private void LogoutButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "Are you sure you want to log out?",
            "Log Out",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (result == MessageBoxResult.Yes)
        {
            // Stop services
            App.ProxyService.DisableProxy();
            App.MitmService.Stop();

            // Log out
            AppState.Instance.Logout();

            Close();
        }
    }

    private void QuitButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "Are you sure you want to quit Oximy?\n\nThis will disable the proxy and stop monitoring AI traffic.",
            "Quit Oximy",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (result == MessageBoxResult.Yes)
        {
            App.Quit();
        }
    }

    private async void CheckUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            CheckUpdateButton.IsEnabled = false;
            UpdateStatusText.Text = "Checking for updates...";

            await Services.UpdateService.Instance.CheckForUpdatesAsync();

            if (Services.UpdateService.Instance.IsUpdateAvailable)
            {
                UpdateStatusText.Text = $"Update available: v{Services.UpdateService.Instance.LatestVersion}";
            }
            else
            {
                UpdateStatusText.Text = "You're up to date!";
            }
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = $"Check failed: {ex.Message}";
        }
        finally
        {
            CheckUpdateButton.IsEnabled = true;
        }
    }

    private async void GenerateCertButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            GenerateCertButton.IsEnabled = false;
            GenerateCertText.Text = "Generating...";

            await App.CertificateService.GenerateCAAsync();

            MessageBox.Show(
                "Certificate generated successfully.\n\nClick 'Install Certificate' to add it to your system's trusted store.",
                "Success",
                MessageBoxButton.OK,
                MessageBoxImage.Information);

            UpdateCertificateUI();
            InstallCertButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Failed to generate certificate: {ex.Message}",
                "Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        finally
        {
            GenerateCertButton.IsEnabled = true;
            UpdateCertificateUI();
        }
    }

    private async void InstallCertButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            // Generate certificate first if it doesn't exist
            if (!App.CertificateService.IsCAGenerated)
            {
                GenerateCertButton.IsEnabled = false;
                InstallCertButton.IsEnabled = false;
                GenerateCertText.Text = "Generating...";

                await App.CertificateService.GenerateCAAsync();

                GenerateCertButton.IsEnabled = true;
                UpdateCertificateUI();
            }

            InstallCertButton.IsEnabled = false;
            InstallCertText.Text = "Installing...";

            var result = MessageBox.Show(
                "This will install the Oximy CA certificate to your system.\n\n" +
                "You may be prompted for administrator access.\n\n" +
                "This is required to monitor HTTPS traffic.",
                "Install Certificate",
                MessageBoxButton.OKCancel,
                MessageBoxImage.Information);

            if (result != MessageBoxResult.OK)
            {
                return;
            }

            await App.CertificateService.InstallCAAsync();

            MessageBox.Show(
                "Certificate installed successfully.\n\nYou can now start monitoring.",
                "Success",
                MessageBoxButton.OK,
                MessageBoxImage.Information);

            UpdateCertificateUI();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Failed to install certificate: {ex.Message}\n\n" +
                "Try running Oximy as Administrator.",
                "Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        finally
        {
            InstallCertButton.IsEnabled = true;
            UpdateCertificateUI();
        }
    }

    private void UninstallCertButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "Are you sure you want to uninstall the Oximy CA certificate?\n\n" +
            "You will need to reinstall it to monitor HTTPS traffic.",
            "Uninstall Certificate",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning);

        if (result != MessageBoxResult.Yes)
        {
            return;
        }

        try
        {
            UninstallCertButton.IsEnabled = false;

            // Stop monitoring first
            App.ProxyService.DisableProxy();
            App.MitmService.Stop();

            App.CertificateService.RemoveCA();

            MessageBox.Show(
                "Certificate uninstalled successfully.",
                "Success",
                MessageBoxButton.OK,
                MessageBoxImage.Information);

            UpdateCertificateUI();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Failed to uninstall certificate: {ex.Message}",
                "Error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        finally
        {
            UninstallCertButton.IsEnabled = true;
            UpdateCertificateUI();
        }
    }

    private static void OpenUrl(string url)
    {
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true
            });
        }
        catch
        {
            // Ignore errors opening URL
        }
    }

    private static void OpenFolder(string path)
    {
        try
        {
            // Ensure directory exists
            Directory.CreateDirectory(path);

            Process.Start(new ProcessStartInfo
            {
                FileName = "explorer.exe",
                Arguments = path
            });
        }
        catch
        {
            // Ignore errors opening folder
        }
    }
}
