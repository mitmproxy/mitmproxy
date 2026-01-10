using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using OximyWindows.Core;
using OximyWindows.Views;

namespace OximyWindows.ViewModels;

public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private bool _isPopupVisible;

    public MainViewModel()
    {
        // Subscribe to state changes
        AppState.Instance.PropertyChanged += (s, e) => OnPropertyChanged(e.PropertyName);
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
        var settingsWindow = new SettingsWindow();
        settingsWindow.Show();
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

    [RelayCommand]
    private void Quit()
    {
        App.Quit();
    }
}
