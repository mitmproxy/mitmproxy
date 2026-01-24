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
    private bool _linkCopied;

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
    /// Matches Mac app structure with permissions object.
    /// </summary>
    private static string CollectDeviceInfo()
    {
        var permissions = new Dictionary<string, bool>
        {
            ["networkCapture"] = true,
            ["systemExtension"] = false,
            ["fullDiskAccess"] = false
        };

        var info = new Dictionary<string, object>
        {
            ["hostname"] = Environment.MachineName,
            ["os"] = "windows",
            ["osVersion"] = $"Windows {Environment.OSVersion.Version}",
            ["sensorVersion"] = Constants.Version,
            ["hardwareId"] = Services.APIClient.GetHardwareId(),
            ["permissions"] = permissions
        };

        var json = JsonSerializer.Serialize(info);
        return Convert.ToBase64String(Encoding.UTF8.GetBytes(json));
    }

    /// <summary>
    /// Build the complete auth URL with state and device info.
    /// </summary>
    private string BuildAuthUrl()
    {
        // Get or generate state for CSRF protection
        var state = Properties.Settings.Default.AuthState;
        if (string.IsNullOrEmpty(state))
        {
            state = Guid.NewGuid().ToString();
            Properties.Settings.Default.AuthState = state;
            Properties.Settings.Default.Save();
        }

        var deviceInfo = CollectDeviceInfo();
        return $"{Constants.AuthUrl}?state={Uri.EscapeDataString(state)}&device_info={Uri.EscapeDataString(deviceInfo)}&callback=oximy://auth/callback";
    }

    /// <summary>
    /// Handle Copy Link button click.
    /// Copies the auth URL to clipboard with visual feedback.
    /// </summary>
    private void OnCopyLinkClick(object sender, RoutedEventArgs e)
    {
        try
        {
            // Generate state if not already set
            var state = Properties.Settings.Default.AuthState;
            if (string.IsNullOrEmpty(state))
            {
                state = Guid.NewGuid().ToString();
                Properties.Settings.Default.AuthState = state;
                Properties.Settings.Default.Save();
            }

            var authUrl = BuildAuthUrl();
            Clipboard.SetText(authUrl);
            Debug.WriteLine($"[EnrollmentView] Copied auth URL to clipboard: {authUrl}");

            // Show checkmark feedback
            _linkCopied = true;
            CopyLinkIcon.Text = "\uE73E"; // Checkmark icon
            CopyLinkButton.ToolTip = "Copied!";

            // Reset after 2 seconds
            Task.Delay(2000).ContinueWith(_ =>
            {
                Dispatcher.Invoke(() =>
                {
                    _linkCopied = false;
                    CopyLinkIcon.Text = "\uE8C8"; // Copy icon
                    CopyLinkButton.ToolTip = "Copy login link";
                });
            });
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[EnrollmentView] Failed to copy auth URL: {ex.Message}");
        }
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
