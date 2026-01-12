using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using Velopack;
using Velopack.Sources;

namespace OximyWindows.Services;

/// <summary>
/// Manages automatic application updates using Velopack.
/// Provides background update checking, download progress tracking, and seamless app restarts.
/// </summary>
/// <remarks>
/// Uses GitHub Releases as the update source. Updates are downloaded in the background
/// and can be applied immediately (with restart) or on next app exit.
///
/// Usage:
/// <code>
/// // Check for updates
/// await UpdateService.Instance.CheckForUpdatesAsync();
///
/// // If update available, download and install
/// if (UpdateService.Instance.IsUpdateAvailable)
/// {
///     await UpdateService.Instance.DownloadAndApplyUpdateAsync();
/// }
/// </code>
/// </remarks>
public class UpdateService : INotifyPropertyChanged
{
    private static UpdateService? _instance;

    /// <summary>
    /// Gets the singleton instance of the UpdateService.
    /// </summary>
    public static UpdateService Instance => _instance ??= new UpdateService();

    private readonly UpdateManager _updateManager;
    private UpdateInfo? _updateInfo;
    private bool _isUpdateAvailable;
    private bool _isCheckingForUpdates;
    private bool _isDownloading;
    private int _downloadProgress;
    private string? _latestVersion;
    private string? _errorMessage;

    /// <summary>
    /// Gets whether an update is available for download.
    /// </summary>
    public bool IsUpdateAvailable
    {
        get => _isUpdateAvailable;
        private set => SetProperty(ref _isUpdateAvailable, value);
    }

    /// <summary>
    /// Gets whether the service is currently checking for updates.
    /// </summary>
    public bool IsCheckingForUpdates
    {
        get => _isCheckingForUpdates;
        private set => SetProperty(ref _isCheckingForUpdates, value);
    }

    /// <summary>
    /// Gets whether an update is currently being downloaded.
    /// </summary>
    public bool IsDownloading
    {
        get => _isDownloading;
        private set => SetProperty(ref _isDownloading, value);
    }

    /// <summary>
    /// Gets the download progress as a percentage (0-100).
    /// </summary>
    public int DownloadProgress
    {
        get => _downloadProgress;
        private set => SetProperty(ref _downloadProgress, value);
    }

    /// <summary>
    /// Gets the latest available version string, if an update is available.
    /// </summary>
    public string? LatestVersion
    {
        get => _latestVersion;
        private set => SetProperty(ref _latestVersion, value);
    }

    /// <summary>
    /// Gets the last error message if an operation failed.
    /// </summary>
    public string? ErrorMessage
    {
        get => _errorMessage;
        private set => SetProperty(ref _errorMessage, value);
    }

    /// <summary>
    /// Gets the current installed version.
    /// </summary>
    public string CurrentVersion => Constants.Version;

    private UpdateService()
    {
        // Use GitHub Releases as the update source
        // This reads from https://github.com/OximyHQ/mitmproxy/releases
        var source = new GithubSource(
            "https://github.com/OximyHQ/mitmproxy",
            accessToken: null,  // Public repo, no token needed
            prerelease: false   // Only stable releases
        );

        _updateManager = new UpdateManager(source);
    }

    /// <summary>
    /// Checks for available updates asynchronously.
    /// </summary>
    /// <returns>True if an update is available, false otherwise.</returns>
    /// <remarks>
    /// This method is safe to call multiple times. If already checking,
    /// subsequent calls will be ignored.
    /// </remarks>
    public async Task<bool> CheckForUpdatesAsync()
    {
        if (IsCheckingForUpdates) return IsUpdateAvailable;

        try
        {
            IsCheckingForUpdates = true;
            ErrorMessage = null;

            System.Diagnostics.Debug.WriteLine("[UpdateService] Checking for updates...");

            _updateInfo = await _updateManager.CheckForUpdatesAsync();

            if (_updateInfo != null)
            {
                IsUpdateAvailable = true;
                LatestVersion = _updateInfo.TargetFullRelease.Version.ToString();

                System.Diagnostics.Debug.WriteLine(
                    $"[UpdateService] Update available: {CurrentVersion} → {LatestVersion}");
            }
            else
            {
                IsUpdateAvailable = false;
                LatestVersion = null;

                System.Diagnostics.Debug.WriteLine(
                    $"[UpdateService] No updates available. Current version: {CurrentVersion}");
            }

            return IsUpdateAvailable;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine(
                $"[UpdateService] Check failed: {ex.Message}");

            ErrorMessage = ex.Message;
            IsUpdateAvailable = false;
            LatestVersion = null;

            return false;
        }
        finally
        {
            IsCheckingForUpdates = false;
        }
    }

    /// <summary>
    /// Downloads the available update and applies it, restarting the application.
    /// </summary>
    /// <remarks>
    /// This method will:
    /// 1. Download the update package with progress updates
    /// 2. Apply the update
    /// 3. Restart the application automatically
    ///
    /// If download fails, the error is shown to the user and the app continues running.
    /// </remarks>
    public async Task DownloadAndApplyUpdateAsync()
    {
        if (_updateInfo == null)
        {
            System.Diagnostics.Debug.WriteLine(
                "[UpdateService] No update info available. Call CheckForUpdatesAsync first.");
            return;
        }

        if (IsDownloading)
        {
            System.Diagnostics.Debug.WriteLine(
                "[UpdateService] Already downloading.");
            return;
        }

        try
        {
            IsDownloading = true;
            DownloadProgress = 0;
            ErrorMessage = null;

            System.Diagnostics.Debug.WriteLine(
                $"[UpdateService] Downloading update {LatestVersion}...");

            // Download with progress callback
            await _updateManager.DownloadUpdatesAsync(
                _updateInfo,
                progress =>
                {
                    DownloadProgress = progress;
                    System.Diagnostics.Debug.WriteLine(
                        $"[UpdateService] Download progress: {progress}%");
                }
            );

            System.Diagnostics.Debug.WriteLine(
                "[UpdateService] Download complete. Applying update and restarting...");

            // Apply update and restart the app
            _updateManager.ApplyUpdatesAndRestart(_updateInfo);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine(
                $"[UpdateService] Update failed: {ex.Message}");

            ErrorMessage = ex.Message;

            // Show error to user on UI thread
            Application.Current.Dispatcher.Invoke(() =>
            {
                MessageBox.Show(
                    $"Failed to download update:\n\n{ex.Message}\n\nPlease try again later or download manually from GitHub.",
                    "Update Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            });
        }
        finally
        {
            IsDownloading = false;
        }
    }

    /// <summary>
    /// Downloads the update without restarting. The update will be applied on next app exit.
    /// </summary>
    /// <remarks>
    /// Use this when you want to download the update in the background but let the user
    /// decide when to restart. Call <see cref="ApplyUpdateOnExit"/> when the app is closing.
    /// </remarks>
    public async Task DownloadUpdateAsync()
    {
        if (_updateInfo == null || IsDownloading) return;

        try
        {
            IsDownloading = true;
            DownloadProgress = 0;
            ErrorMessage = null;

            await _updateManager.DownloadUpdatesAsync(
                _updateInfo,
                progress => DownloadProgress = progress
            );

            System.Diagnostics.Debug.WriteLine(
                "[UpdateService] Download complete. Update will be applied on exit.");
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
            System.Diagnostics.Debug.WriteLine(
                $"[UpdateService] Download failed: {ex.Message}");
        }
        finally
        {
            IsDownloading = false;
        }
    }

    /// <summary>
    /// Applies the downloaded update and exits the application.
    /// Call this during app shutdown to apply pending updates.
    /// </summary>
    public void ApplyUpdateOnExit()
    {
        if (_updateInfo != null && DownloadProgress == 100)
        {
            System.Diagnostics.Debug.WriteLine(
                "[UpdateService] Applying update on exit...");

            _updateManager.ApplyUpdatesAndExit(_updateInfo);
        }
    }

    /// <summary>
    /// Waits for pending updates to finish and applies them.
    /// Call this if the app was launched to finalize an update.
    /// </summary>
    public void WaitForPendingUpdates()
    {
        try
        {
            _updateManager.WaitExitThenApplyUpdates(_updateInfo);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine(
                $"[UpdateService] WaitForPendingUpdates error: {ex.Message}");
        }
    }

    #region INotifyPropertyChanged

    /// <inheritdoc />
    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>
    /// Sets a property value and raises PropertyChanged if the value changed.
    /// </summary>
    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    #endregion
}
