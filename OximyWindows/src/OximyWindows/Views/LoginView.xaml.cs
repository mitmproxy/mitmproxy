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

            // TODO: Replace with actual API call
            // For now, simulate verification
            await Task.Delay(1000);

            // Simulate success (in production, this would call the API)
            var workspaceName = "Demo Workspace";
            var deviceToken = Guid.NewGuid().ToString();

            // In production:
            // var response = await VerifyWithApiAsync(code);
            // workspaceName = response.WorkspaceName;
            // deviceToken = response.DeviceToken;

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
            code,
            device_name = AppState.Instance.DeviceName,
            platform = "windows"
        };

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync($"{Constants.ApiBaseUrl}/v1/auth/verify", content);

        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception(response.StatusCode == System.Net.HttpStatusCode.Unauthorized
                ? "Invalid code. Please try again."
                : $"Verification failed: {response.StatusCode}");
        }

        var responseBody = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<VerifyResponse>(responseBody);

        return (result?.WorkspaceName ?? "Workspace", result?.DeviceToken ?? "");
    }

    private class VerifyResponse
    {
        public string? WorkspaceName { get; set; }
        public string? DeviceToken { get; set; }
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
