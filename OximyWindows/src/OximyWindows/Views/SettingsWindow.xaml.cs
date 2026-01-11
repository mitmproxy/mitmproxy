using System.Diagnostics;
using System.IO;
using System.Windows;
using OximyWindows.Core;
using OximyWindows.Services;

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

        // Initialize update status
        UpdateUpdateStatusText();

        // Subscribe to update service property changes
        UpdateService.Instance.PropertyChanged += (s, args) =>
        {
            Dispatcher.Invoke(() =>
            {
                if (args.PropertyName == nameof(UpdateService.DownloadProgress))
                {
                    UpdateProgressBar.Value = UpdateService.Instance.DownloadProgress;
                }
                else if (args.PropertyName == nameof(UpdateService.IsUpdateAvailable) ||
                         args.PropertyName == nameof(UpdateService.LatestVersion) ||
                         args.PropertyName == nameof(UpdateService.IsCheckingForUpdates))
                {
                    UpdateUpdateStatusText();
                }
            });
        };
    }

    /// <summary>
    /// Updates the update status text based on current UpdateService state.
    /// </summary>
    private void UpdateUpdateStatusText()
    {
        var service = UpdateService.Instance;

        if (service.IsUpdateAvailable && !string.IsNullOrEmpty(service.LatestVersion))
        {
            UpdateStatusText.Text = $"Version {service.LatestVersion} available";
            UpdateStatusText.Foreground = FindResource("AccentBrush") as System.Windows.Media.Brush
                                          ?? System.Windows.Media.Brushes.Orange;
            CheckUpdateButton.Content = "Download & Install";
        }
        else
        {
            UpdateStatusText.Text = $"Current version: {Constants.Version}";
            UpdateStatusText.Foreground = FindResource("TextSecondaryBrush") as System.Windows.Media.Brush
                                          ?? System.Windows.Media.Brushes.Gray;
            CheckUpdateButton.Content = "Check for Updates";
        }
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }

    /// <summary>
    /// Handles the Check for Updates button click.
    /// If no update is available, checks for updates.
    /// If an update is available, downloads and installs it.
    /// </summary>
    private async void CheckUpdateButton_Click(object sender, RoutedEventArgs e)
    {
        var service = UpdateService.Instance;

        // If update is already available, download and install
        if (service.IsUpdateAvailable)
        {
            CheckUpdateButton.IsEnabled = false;
            CheckUpdateButton.Content = "Downloading...";
            UpdateProgressBar.Visibility = Visibility.Visible;
            UpdateProgressBar.Value = 0;

            await service.DownloadAndApplyUpdateAsync();

            // If we get here, the download failed (otherwise app would have restarted)
            CheckUpdateButton.IsEnabled = true;
            UpdateProgressBar.Visibility = Visibility.Collapsed;
            UpdateUpdateStatusText();
        }
        else
        {
            // Check for updates
            CheckUpdateButton.IsEnabled = false;
            CheckUpdateButton.Content = "Checking...";

            var hasUpdate = await service.CheckForUpdatesAsync();

            CheckUpdateButton.IsEnabled = true;

            if (hasUpdate)
            {
                UpdateUpdateStatusText();
            }
            else
            {
                MessageBox.Show(
                    "You're running the latest version!",
                    "No Updates Available",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
                CheckUpdateButton.Content = "Check for Updates";
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
