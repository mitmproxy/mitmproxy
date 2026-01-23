using System.Diagnostics;
using System.Windows;
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

    private void TermsButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.TermsUrl);
    }

    private void PrivacyButton_Click(object sender, RoutedEventArgs e)
    {
        OpenUrl(Constants.PrivacyUrl);
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

    protected override void OnClosed(EventArgs e)
    {
        // Clean up event handlers
        Loaded -= OnLoaded;
        base.OnClosed(e);
    }
}
