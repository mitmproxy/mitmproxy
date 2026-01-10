using System.Diagnostics;
using System.IO;
using System.Windows;
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
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        Close();
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
