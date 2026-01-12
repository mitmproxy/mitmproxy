using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using OximyWindows.Core;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Enrollment view for entering the 6-digit workspace code.
/// Matches the Mac app's EnrollmentView functionality.
/// </summary>
public partial class EnrollmentView : UserControl
{
    private readonly TextBox[] _digitBoxes;
    private bool _isProcessing;

    public EnrollmentView()
    {
        InitializeComponent();

        _digitBoxes = [Digit1, Digit2, Digit3, Digit4, Digit5, Digit6];

        // Set initial focus
        Loaded += (s, e) => Digit1.Focus();

        // Handle paste from clipboard
        DataObject.AddPastingHandler(Digit1, OnPaste);
    }

    /// <summary>
    /// Get the full 6-digit code.
    /// </summary>
    private string GetCode()
    {
        return string.Concat(_digitBoxes.Select(tb => tb.Text));
    }

    /// <summary>
    /// Check if code is complete (all 6 digits filled).
    /// </summary>
    private bool IsCodeComplete()
    {
        return _digitBoxes.All(tb => tb.Text.Length == 1 && char.IsDigit(tb.Text[0]));
    }

    /// <summary>
    /// Update button state based on code completeness.
    /// </summary>
    private void UpdateButtonState()
    {
        ConnectButton.IsEnabled = IsCodeComplete() && !_isProcessing;
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
    /// Handle digit input validation - only allow single digits.
    /// </summary>
    private void OnDigitPreviewTextInput(object sender, TextCompositionEventArgs e)
    {
        // Only allow single digits
        e.Handled = !char.IsDigit(e.Text[0]);
    }

    /// <summary>
    /// Handle key navigation and deletion.
    /// </summary>
    private void OnDigitKeyDown(object sender, KeyEventArgs e)
    {
        var textBox = (TextBox)sender;
        var index = Array.IndexOf(_digitBoxes, textBox);

        switch (e.Key)
        {
            case Key.Back:
                if (textBox.Text.Length == 0 && index > 0)
                {
                    // Move to previous box and clear it
                    _digitBoxes[index - 1].Text = string.Empty;
                    _digitBoxes[index - 1].Focus();
                    e.Handled = true;
                }
                else if (textBox.Text.Length > 0)
                {
                    // Clear current box
                    textBox.Text = string.Empty;
                    e.Handled = true;
                }
                ClearError();
                break;

            case Key.Delete:
                textBox.Text = string.Empty;
                ClearError();
                e.Handled = true;
                break;

            case Key.Left:
                if (index > 0)
                {
                    _digitBoxes[index - 1].Focus();
                    e.Handled = true;
                }
                break;

            case Key.Right:
                if (index < _digitBoxes.Length - 1)
                {
                    _digitBoxes[index + 1].Focus();
                    e.Handled = true;
                }
                break;

            case Key.Tab:
                // Let Tab work normally for accessibility
                break;

            case Key.Enter:
                if (IsCodeComplete())
                {
                    OnConnectClick(this, new RoutedEventArgs());
                }
                e.Handled = true;
                break;

            case Key.V:
                if (Keyboard.Modifiers == ModifierKeys.Control)
                {
                    // Handle Ctrl+V paste
                    HandlePaste();
                    e.Handled = true;
                }
                break;
        }
    }

    /// <summary>
    /// Handle text changed - auto advance to next field.
    /// </summary>
    private void OnDigitTextChanged(object sender, TextChangedEventArgs e)
    {
        var textBox = (TextBox)sender;
        var index = Array.IndexOf(_digitBoxes, textBox);

        // If a digit was entered, move to next field
        if (textBox.Text.Length == 1 && char.IsDigit(textBox.Text[0]))
        {
            if (index < _digitBoxes.Length - 1)
            {
                _digitBoxes[index + 1].Focus();
            }
        }

        UpdateButtonState();
    }

    /// <summary>
    /// Select all text when focused.
    /// </summary>
    private void OnDigitGotFocus(object sender, RoutedEventArgs e)
    {
        var textBox = (TextBox)sender;
        textBox.SelectAll();
    }

    /// <summary>
    /// Handle paste event.
    /// </summary>
    private void OnPaste(object sender, DataObjectPastingEventArgs e)
    {
        e.CancelCommand();
        HandlePaste();
    }

    /// <summary>
    /// Handle paste from clipboard.
    /// </summary>
    private void HandlePaste()
    {
        if (Clipboard.ContainsText())
        {
            var text = Clipboard.GetText();
            var digits = new string(text.Where(char.IsDigit).Take(6).ToArray());

            if (digits.Length > 0)
            {
                ClearError();

                for (int i = 0; i < _digitBoxes.Length; i++)
                {
                    _digitBoxes[i].Text = i < digits.Length ? digits[i].ToString() : string.Empty;
                }

                // Focus the next empty field or last field
                var nextEmpty = _digitBoxes.FirstOrDefault(tb => tb.Text.Length == 0);
                (nextEmpty ?? _digitBoxes[^1]).Focus();

                UpdateButtonState();
            }
        }
    }

    /// <summary>
    /// Handle connect button click.
    /// </summary>
    private async void OnConnectClick(object sender, RoutedEventArgs e)
    {
        if (_isProcessing || !IsCodeComplete())
            return;

        var code = GetCode();
        ClearError();

        _isProcessing = true;
        ConnectButton.Visibility = Visibility.Collapsed;
        LoadingPanel.Visibility = Visibility.Visible;

        try
        {
            var response = await APIClient.Instance.RegisterDeviceAsync(code);

            // Store credentials and transition to Setup phase
            AppState.Instance.CompleteEnrollment(
                response.DeviceId,
                response.DeviceToken,
                response.WorkspaceName,
                response.WorkspaceId);

            Debug.WriteLine($"[EnrollmentView] Device registered: {response.DeviceId}");
        }
        catch (ApiException ex)
        {
            string errorMessage = ex.StatusCode switch
            {
                System.Net.HttpStatusCode.BadRequest when ex.Message.Contains("expired") =>
                    "This code has expired. Please get a new code.",
                System.Net.HttpStatusCode.BadRequest =>
                    "Invalid enrollment code. Please check and try again.",
                System.Net.HttpStatusCode.NotFound =>
                    "Code not found. Please check and try again.",
                System.Net.HttpStatusCode.Conflict =>
                    "This device is already registered.",
                System.Net.HttpStatusCode.TooManyRequests =>
                    "Too many attempts. Please wait and try again.",
                _ when ex.IsNetworkError =>
                    "Network error. Please check your connection.",
                _ =>
                    $"Error: {ex.Message}"
            };

            ShowError(errorMessage);
            Debug.WriteLine($"[EnrollmentView] Registration failed: {ex.Message}");
        }
        catch (Exception ex)
        {
            ShowError("An unexpected error occurred. Please try again.");
            Debug.WriteLine($"[EnrollmentView] Unexpected error: {ex.Message}");
        }
        finally
        {
            _isProcessing = false;
            ConnectButton.Visibility = Visibility.Visible;
            LoadingPanel.Visibility = Visibility.Collapsed;
            UpdateButtonState();
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
