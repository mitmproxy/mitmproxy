using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class LoginView : UserControl
{
    private readonly TextBox[] _digitBoxes;
    private static readonly HttpClient _httpClient = new();

    public LoginView()
    {
        InitializeComponent();

        _digitBoxes = new[] { Digit1, Digit2, Digit3, Digit4, Digit5, Digit6 };

        // Focus first digit on load
        Loaded += (s, e) => Digit1.Focus();
    }

    private void Digit_PreviewTextInput(object sender, TextCompositionEventArgs e)
    {
        // Only allow digits
        e.Handled = !char.IsDigit(e.Text, 0);
    }

    private async void Digit_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (sender is not TextBox currentBox)
            return;

        // Auto-advance to next digit
        if (currentBox.Text.Length == 1)
        {
            var currentIndex = Array.IndexOf(_digitBoxes, currentBox);
            if (currentIndex < _digitBoxes.Length - 1)
            {
                _digitBoxes[currentIndex + 1].Focus();
            }
            else
            {
                // Last digit entered - try to verify
                await VerifyCodeAsync();
            }
        }

        // Handle backspace - go to previous digit
        if (currentBox.Text.Length == 0)
        {
            var currentIndex = Array.IndexOf(_digitBoxes, currentBox);
            if (currentIndex > 0)
            {
                _digitBoxes[currentIndex - 1].Focus();
            }
        }

        // Clear error when typing
        ErrorText.Visibility = Visibility.Collapsed;
    }

    private string GetCode()
    {
        return string.Concat(_digitBoxes.Select(tb => tb.Text));
    }

    private async Task VerifyCodeAsync()
    {
        var code = GetCode();
        if (code.Length != 6)
            return;

        try
        {
            // Show loading
            LoadingPanel.Visibility = Visibility.Visible;
            ErrorText.Visibility = Visibility.Collapsed;
            SetInputsEnabled(false);

            // Call the actual API
            var response = await VerifyWithApiAsync(code);
            var workspaceName = response.WorkspaceName;
            var deviceToken = response.DeviceToken;

            // Complete login
            AppState.Instance.CompleteLogin(workspaceName, deviceToken);
        }
        catch (Exception ex)
        {
            ShowError(ex.Message);
            ClearCode();
        }
        finally
        {
            LoadingPanel.Visibility = Visibility.Collapsed;
            SetInputsEnabled(true);
        }
    }

    private async Task<(string WorkspaceName, string DeviceToken)> VerifyWithApiAsync(string code)
    {
        var requestBody = new
        {
            hostname = Environment.MachineName,
            displayName = AppState.Instance.DeviceName,
            os = "windows",
            osVersion = Environment.OSVersion.VersionString,
            sensorVersion = Constants.Version,
            hardwareId = GetHardwareId(),
            permissions = new
            {
                networkCapture = true,
                systemExtension = false,
                fullDiskAccess = false
            }
        };

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        using var request = new HttpRequestMessage(HttpMethod.Post, $"{Constants.ApiBaseUrl}/devices/register");
        request.Content = content;
        request.Headers.Add("X-Enrollment-Token", code);

        var response = await _httpClient.SendAsync(request);

        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception(response.StatusCode == System.Net.HttpStatusCode.Unauthorized
                ? "Invalid code. Please try again."
                : response.StatusCode == System.Net.HttpStatusCode.BadRequest
                    ? "Invalid or expired code. Please try again."
                    : $"Verification failed: {response.StatusCode}");
        }

        var responseBody = await response.Content.ReadAsStringAsync();
        var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        var result = JsonSerializer.Deserialize<DeviceRegistrationResponse>(responseBody, options);

        if (result?.Success != true || result.Data == null)
        {
            throw new Exception(result?.Error?.Message ?? "Registration failed");
        }

        // Use workspaceName if available, fall back to workspaceId
        var workspaceName = result.Data.WorkspaceName ?? result.Data.WorkspaceId;
        return (workspaceName, result.Data.DeviceToken);
    }

    private static string GetHardwareId()
    {
        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Cryptography");
            return key?.GetValue("MachineGuid")?.ToString() ?? Guid.NewGuid().ToString();
        }
        catch
        {
            return Guid.NewGuid().ToString();
        }
    }

    private class DeviceRegistrationResponse
    {
        public bool Success { get; set; }
        public DeviceData? Data { get; set; }
        public ApiError? Error { get; set; }
    }

    private class DeviceData
    {
        public string DeviceId { get; set; } = "";
        public string DeviceName { get; set; } = "";
        public string DeviceToken { get; set; } = "";
        public string WorkspaceId { get; set; } = "";
        public string? WorkspaceName { get; set; }
    }

    private class ApiError
    {
        public string? Code { get; set; }
        public string? Message { get; set; }
    }

    private void ShowError(string message)
    {
        ErrorText.Text = message;
        ErrorText.Visibility = Visibility.Visible;
    }

    private void ClearCode()
    {
        foreach (var box in _digitBoxes)
        {
            box.Text = string.Empty;
        }
        Digit1.Focus();
    }

    private void SetInputsEnabled(bool enabled)
    {
        foreach (var box in _digitBoxes)
        {
            box.IsEnabled = enabled;
        }
    }

    private void SignUpLink_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = Constants.SignUpUrl,
                UseShellExecute = true
            });
        }
        catch
        {
            // Ignore errors opening URL
        }
    }
}
