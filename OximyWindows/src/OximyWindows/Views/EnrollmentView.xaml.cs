using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace OximyWindows.Views;

/// <summary>
/// Enrollment view for browser-based authentication.
/// Opens a browser to authenticate, then receives a callback via oximy:// URL scheme.
/// </summary>
public partial class EnrollmentView : UserControl
{
    private bool _isLoading;

    public EnrollmentView()
    {
        InitializeComponent();
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
    /// Show error message.
    /// </summary>
    private void ShowError(string message)
    {
        ErrorText.Text = message;
        ErrorText.Visibility = Visibility.Visible;
    }

    /// <summary>
    /// Update button state based on loading status.
    /// </summary>
    private void UpdateButtonState()
    {
        LoginButton.IsEnabled = !_isLoading;

        if (_isLoading)
        {
            ButtonIcon.Text = "\uE895"; // Sync icon (spinning)
            ButtonText.Text = "Opening Browser...";
        }
        else
        {
            ButtonIcon.Text = "\uE8A7"; // Open external icon
            ButtonText.Text = "Login with Browser";
        }
    }

    /// <summary>
    /// Handle Login with Browser button click.
    /// Generates CSRF state, opens browser with auth URL.
    /// </summary>
    private void OnLoginWithBrowserClick(object sender, RoutedEventArgs e)
    {
        if (_isLoading) return;

        Debug.WriteLine("[EnrollmentView] OnLoginWithBrowserClick called");

        _isLoading = true;
        ClearError();
        UpdateButtonState();

        try
        {
            // Generate and store state for CSRF protection
            var state = Guid.NewGuid().ToString();
            Properties.Settings.Default.AuthState = state;
            Properties.Settings.Default.Save();
            Debug.WriteLine($"[EnrollmentView] State generated: {state}");

            // Collect device info to send to auth page
            var deviceInfo = CollectDeviceInfo();

            // Build auth URL
            var authUrl = $"{Constants.AuthUrl}?state={Uri.EscapeDataString(state)}&device_info={Uri.EscapeDataString(deviceInfo)}&callback=oximy://auth/callback";

            Debug.WriteLine($"[EnrollmentView] Opening URL: {authUrl}");

            // Open browser
            var success = Process.Start(new ProcessStartInfo
            {
                FileName = authUrl,
                UseShellExecute = true
            }) != null;

            Debug.WriteLine($"[EnrollmentView] Process.Start returned: {success}");

            if (!success)
            {
                ShowError("Failed to open browser. Please try again.");
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[EnrollmentView] Error opening browser: {ex.Message}");
            ShowError("Failed to open browser. Please try again.");
        }

        // Reset loading state after a delay (user is now in browser)
        Task.Delay(2000).ContinueWith(_ =>
        {
            Dispatcher.Invoke(() =>
            {
                _isLoading = false;
                UpdateButtonState();
            });
        });
    }

    /// <summary>
    /// Collect device info to send to the auth page.
    /// </summary>
    private static string CollectDeviceInfo()
    {
        var info = new Dictionary<string, string>
        {
            ["hostname"] = Environment.MachineName,
            ["os_version"] = $"Windows {Environment.OSVersion.Version}",
            ["sensor_version"] = Constants.Version
        };

        var json = JsonSerializer.Serialize(info);
        return Convert.ToBase64String(Encoding.UTF8.GetBytes(json));
    }

    /// <summary>
    /// Handle sign up link click.
    /// </summary>
    private void OnSignUpClick(object sender, RoutedEventArgs e)
    {
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = Constants.SignUpUrl,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[EnrollmentView] Failed to open signup URL: {ex.Message}");
        }
    }
}
