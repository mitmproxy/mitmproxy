using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using OximyWindows.Core;

namespace OximyWindows.Views;

public partial class OnboardingView : UserControl
{
    private int _currentPage;

    private readonly (string Title, string Subtitle)[] _pages =
    {
        ("Welcome to Oximy", "Monitor and analyze your AI API usage across all applications."),
        ("Your Privacy Matters", "All data is stored locally on your device. We never collect or share your AI conversations."),
        ("Ready to Start", "Let's set up Oximy to capture your AI traffic securely.")
    };

    public OnboardingView()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        UpdatePage();
    }

    private void UpdatePage()
    {
        var page = _pages[_currentPage];
        TitleText.Text = page.Title;
        SubtitleText.Text = page.Subtitle;

        // Update indicators using TryFindResource for safety
        var accentBrush = TryFindResource("AccentBrush") as SolidColorBrush ?? Brushes.Orange;
        var borderBrush = TryFindResource("BorderBrush") as SolidColorBrush ?? Brushes.LightGray;

        Indicator1.Fill = _currentPage >= 0 ? accentBrush : borderBrush;
        Indicator2.Fill = _currentPage >= 1 ? accentBrush : borderBrush;
        Indicator3.Fill = _currentPage >= 2 ? accentBrush : borderBrush;

        // Update navigation
        BackButton.Visibility = _currentPage > 0 ? Visibility.Visible : Visibility.Collapsed;
        NextButton.Content = _currentPage == _pages.Length - 1 ? "Get Started" : "Next";
    }

    private void BackButton_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage > 0)
        {
            _currentPage--;
            UpdatePage();
        }
    }

    private void NextButton_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage < _pages.Length - 1)
        {
            _currentPage++;
            UpdatePage();
        }
        else
        {
            // Complete onboarding
            AppState.Instance.CompleteOnboarding();
        }
    }
}
