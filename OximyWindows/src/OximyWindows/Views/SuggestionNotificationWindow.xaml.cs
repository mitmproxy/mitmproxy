using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using OximyWindows.Services;

namespace OximyWindows.Views;

/// <summary>
/// Non-activating floating suggestion panel (top-right, 30s auto-dismiss).
/// Mirror of SuggestionNotificationView.swift on Mac.
/// </summary>
public partial class SuggestionNotificationWindow : Window
{
    private const int GWL_EXSTYLE    = -20;
    private const int WS_EX_NOACTIVATE = 0x08000000;

    [DllImport("user32.dll")]
    private static extern int GetWindowLong(IntPtr hwnd, int index);

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hwnd, int index, int value);

    private readonly PlaybookSuggestion _suggestion;
    private readonly DispatcherTimer _dismissTimer;
    private bool _actioned;

    public SuggestionNotificationWindow(PlaybookSuggestion suggestion)
    {
        InitializeComponent();
        _suggestion = suggestion;
        PopulateUI(suggestion);
        PositionTopRight();

        _dismissTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
        _dismissTimer.Tick += (_, _) =>
        {
            if (!_actioned) SuggestionService.Instance.DismissSuggestion(_suggestion.Id);
            HideWindow();
        };

        Loaded += OnLoaded;
    }

    private void PopulateUI(PlaybookSuggestion suggestion)
    {
        PlaybookNameText.Text  = suggestion.Playbook.Name;
        DescriptionText.Text   = suggestion.Playbook.Description;
        CategoryTagText.Text   = suggestion.Playbook.Category;
        CategoryIconText.Text  = CategoryIcon(suggestion.Playbook.Category);
    }

    private static string CategoryIcon(string category) => category.ToLowerInvariant() switch
    {
        "coding"    => "\uE943",  // Code
        "writing"   => "\uE8A5",  // Document
        "analysis"  => "\uE9D2",  // Chart
        "research"  => "\uE721",  // Search
        _           => "\uE82F",  // Lightbulb (default)
    };

    private void PositionTopRight()
    {
        var workArea = SystemParameters.WorkArea;
        Left = workArea.Right - Width - 16;
        Top  = workArea.Top + 16;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        var style = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE);

        var fadeIn  = new DoubleAnimation(0, 1, TimeSpan.FromSeconds(0.3));
        var slideIn = new DoubleAnimation(20, 0, TimeSpan.FromSeconds(0.3))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };

        BeginAnimation(OpacityProperty, fadeIn);
        SlideTransform.BeginAnimation(TranslateTransform.YProperty, slideIn);
        _dismissTimer.Start();
    }

    private void HideWindow()
    {
        _dismissTimer.Stop();
        var fadeOut  = new DoubleAnimation(1, 0, TimeSpan.FromSeconds(0.25));
        var slideOut = new DoubleAnimation(0, 20, TimeSpan.FromSeconds(0.25));
        slideOut.Completed += (_, _) => Close();
        BeginAnimation(OpacityProperty, fadeOut);
        SlideTransform.BeginAnimation(TranslateTransform.YProperty, slideOut);
    }

    private async void UseButton_Click(object sender, RoutedEventArgs e)
    {
        if (_actioned) return;
        _actioned = true;
        _dismissTimer.Stop();   // prevent concurrent HideWindow() from the auto-dismiss timer

        Clipboard.SetText(_suggestion.Playbook.PromptTemplate);
        UseButton.Content = "✓ Copied!";

        await Task.Delay(1000);
        SuggestionService.Instance.UseSuggestion(_suggestion.Id);
        HideWindow();
    }

    private void DismissButton_Click(object sender, RoutedEventArgs e)
    {
        _actioned = true;
        SuggestionService.Instance.DismissSuggestion(_suggestion.Id);
        HideWindow();
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        if (!_actioned)
            SuggestionService.Instance.DismissSuggestion(_suggestion.Id);
        _actioned = true;
        HideWindow();
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        var hwnd = new WindowInteropHelper(this).Handle;
        var style = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE);
    }
}
