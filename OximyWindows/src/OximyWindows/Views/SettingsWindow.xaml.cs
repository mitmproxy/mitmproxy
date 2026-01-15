using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Media;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class SettingsWindow : Window
{
    // Singleton pattern to prevent multiple windows
    private static SettingsWindow? _instance;

    /// <summary>
    /// Shows the settings window, creating it if necessary or bringing existing to front.
    /// </summary>
    public static void ShowInstance()
    {
        if (_instance == null)
        {
            _instance = new SettingsWindow();
            _instance.Closed += (s, e) => _instance = null;
        }

        if (_instance.WindowState == WindowState.Minimized)
            _instance.WindowState = WindowState.Normal;

        _instance.Show();
        _instance.Activate();
        _instance.Focus();
    }

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

    private async void UpdateCertificateUI()
    {
        // Run on background thread to avoid blocking UI
        // X509Store operations can take 100-500ms+
        await Task.Run(() => App.CertificateService.CheckStatus());

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

    // Store reference to handler so we can unsubscribe
    private System.ComponentModel.PropertyChangedEventHandler? _downloadProgressHandler;

    private async void DownloadUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            CheckUpdateButton.IsEnabled = false;
            CheckUpdateButton.Content = "Downloading...";
            UpdateProgressBar.Visibility = Visibility.Visible;
            UpdateProgressBar.Value = 0;

            // Unsubscribe previous handler if any
            if (_downloadProgressHandler != null)
            {
                Services.UpdateService.Instance.PropertyChanged -= _downloadProgressHandler;
            }

            // Create and subscribe to progress updates
            _downloadProgressHandler = (s, args) =>
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
            Services.UpdateService.Instance.PropertyChanged += _downloadProgressHandler;

            await Services.UpdateService.Instance.DownloadAndApplyUpdateAsync();
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = $"Download failed: {ex.Message}";
            CheckUpdateButton.Content = "Retry Download";
            UpdateProgressBar.Visibility = Visibility.Collapsed;
            CheckUpdateButton.IsEnabled = true;
        }
        finally
        {
            // Unsubscribe when done
            if (_downloadProgressHandler != null)
            {
                Services.UpdateService.Instance.PropertyChanged -= _downloadProgressHandler;
                _downloadProgressHandler = null;
            }
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

    private async void LogoutButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "Are you sure you want to log out?",
            "Log Out",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (result == MessageBoxResult.Yes)
        {
            // Disable window to prevent double-clicks while logging out
            IsEnabled = false;

            // Run blocking operations on background thread to avoid UI freeze
            await Task.Run(() =>
            {
                App.ProxyService.DisableProxy();
                App.MitmService.Stop();
                App.HeartbeatService.Stop();
                App.SyncService.Stop();
            });

            // Log out (sets Phase = Enrollment) - must be on UI thread
            AppState.Instance.Logout();

            // Close this window
            Close();

            // Show the tray popup with enrollment view so user can log back in
            if (Application.Current.MainWindow is MainWindow mainWindow)
            {
                mainWindow.ShowPopup();
            }
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

    protected override void OnClosed(EventArgs e)
    {
        // Clean up event handlers
        Loaded -= OnLoaded;

        // Unsubscribe download progress handler if attached
        if (_downloadProgressHandler != null)
        {
            Services.UpdateService.Instance.PropertyChanged -= _downloadProgressHandler;
            _downloadProgressHandler = null;
        }

        base.OnClosed(e);
    }
}
