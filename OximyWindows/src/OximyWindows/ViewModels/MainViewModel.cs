using System.ComponentModel;
using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using OximyWindows.Core;
using OximyWindows.Services;
using OximyWindows.Views;

namespace OximyWindows.ViewModels;

public partial class MainViewModel : ObservableObject, IDisposable
{
    [ObservableProperty]
    private bool _isPopupVisible;

    private bool _disposed;

    public MainViewModel()
    {
        // Subscribe to state changes with a named handler for proper cleanup
        AppState.Instance.PropertyChanged += OnAppStateChanged;
    }

    private void OnAppStateChanged(object? sender, PropertyChangedEventArgs e)
    {
        OnPropertyChanged(e.PropertyName);
    }

    [RelayCommand]
    private void TogglePopup()
    {
        if (Application.Current.MainWindow is MainWindow mainWindow)
        {
            mainWindow.TogglePopup();
        }
    }

    [RelayCommand]
    private void ShowPopup()
    {
        if (Application.Current.MainWindow is MainWindow mainWindow)
        {
            mainWindow.ShowPopup();
        }
    }

    [RelayCommand]
    private void OpenSettings()
    {
        SettingsWindow.ShowInstance();
    }

    [RelayCommand]
    private void OpenFeedback()
    {
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = Constants.FeedbackUrl,
                UseShellExecute = true
            });
        }
        catch
        {
            // Ignore errors opening URL
        }
    }

    /// <summary>
    /// Whether the user can quit. Returns false if blocked by MDM policy.
    /// </summary>
    public bool CanQuit => !MDMConfigService.Instance.DisableQuit;

    [RelayCommand(CanExecute = nameof(CanQuit))]
    private void Quit()
    {
        // Double-check MDM policy (in case CanExecute wasn't re-evaluated)
        if (MDMConfigService.Instance.DisableQuit)
        {
            MessageBox.Show(
                "Quitting is disabled by your organization's policy.",
                "Cannot Quit",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
            return;
        }

        App.Quit();
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            AppState.Instance.PropertyChanged -= OnAppStateChanged;
            _disposed = true;
        }
    }
}
