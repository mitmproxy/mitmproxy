import Foundation
import Sparkle

/// Manages automatic application updates using the Sparkle framework.
///
/// `UpdateService` provides a Swift-friendly wrapper around Sparkle's `SPUStandardUpdaterController`,
/// enabling automatic update checks, user-initiated update checks, and observable update state.
///
/// ## Usage
///
/// Initialize the service early in your app's lifecycle (e.g., in `applicationDidFinishLaunching`):
///
/// ```swift
/// // Check for updates in background after launch
/// Task {
///     try? await Task.sleep(for: .seconds(5))
///     await UpdateService.shared.checkForUpdatesInBackground()
/// }
/// ```
///
/// For user-initiated update checks (e.g., from a "Check for Updates" menu item):
///
/// ```swift
/// Button("Check for Updates") {
///     UpdateService.shared.checkForUpdates()
/// }
/// .disabled(!UpdateService.shared.canCheckForUpdates)
/// ```
///
/// ## Configuration
///
/// The appcast URL is configured via the `SUFeedURL` key in Info.plist:
/// ```xml
/// <key>SUFeedURL</key>
/// <string>https://github.com/OximyHQ/mitmproxy/releases/latest/download/appcast.xml</string>
/// ```
@MainActor
final class UpdateService: NSObject, ObservableObject {
    /// Shared singleton instance.
    static let shared = UpdateService()

    // MARK: - Published Properties

    /// Whether the updater is ready to check for updates.
    @Published private(set) var canCheckForUpdates = false

    /// Whether an update check is currently in progress.
    @Published private(set) var isCheckingForUpdates = false

    /// Whether an update is available for download.
    @Published private(set) var updateAvailable = false

    /// The latest available version string, if an update is available.
    @Published private(set) var latestVersion: String?

    /// The date of the last successful update check.
    @Published private(set) var lastUpdateCheckDate: Date?

    /// Any error that occurred during the last update check.
    @Published private(set) var lastError: Error?

    // MARK: - Private Properties

    /// The Sparkle updater controller instance.
    private var updaterController: SPUStandardUpdaterController!

    // MARK: - Initialization

    private override init() {
        super.init()

        // Initialize Sparkle updater controller
        // startingUpdater: true = automatically start checking for updates
        // updaterDelegate: self = receive callbacks about update status
        // userDriverDelegate: self = customize update UI behavior
        updaterController = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: self,
            userDriverDelegate: self
        )

        // Bind to updater's canCheckForUpdates property using Combine
        updaterController.updater.publisher(for: \.canCheckForUpdates)
            .receive(on: DispatchQueue.main)
            .assign(to: &$canCheckForUpdates)

        // Bind to lastUpdateCheckDate
        updaterController.updater.publisher(for: \.lastUpdateCheckDate)
            .receive(on: DispatchQueue.main)
            .assign(to: &$lastUpdateCheckDate)

        print("[UpdateService] Initialized with Sparkle \(SPUUpdater.self)")
    }

    // MARK: - Public API

    /// Checks for updates and shows the standard Sparkle update dialog if an update is found.
    ///
    /// This is typically called from a "Check for Updates" menu item or button.
    /// The update dialog will be shown if an update is available.
    func checkForUpdates() {
        print("[UpdateService] User-initiated update check")
        updaterController.checkForUpdates(nil)
    }

    /// Checks for updates silently in the background.
    ///
    /// If an update is available, Sparkle will show a gentle notification
    /// (depending on configuration). This is suitable for automatic checks on app launch.
    func checkForUpdatesInBackground() {
        print("[UpdateService] Background update check")
        updaterController.updater.checkForUpdatesInBackground()
    }

    /// Whether Sparkle should automatically check for updates.
    var automaticallyChecksForUpdates: Bool {
        get { updaterController.updater.automaticallyChecksForUpdates }
        set {
            updaterController.updater.automaticallyChecksForUpdates = newValue
            print("[UpdateService] automaticallyChecksForUpdates = \(newValue)")
        }
    }

    /// Whether Sparkle should automatically download updates.
    var automaticallyDownloadsUpdates: Bool {
        get { updaterController.updater.automaticallyDownloadsUpdates }
        set {
            updaterController.updater.automaticallyDownloadsUpdates = newValue
            print("[UpdateService] automaticallyDownloadsUpdates = \(newValue)")
        }
    }

    /// The interval (in seconds) between automatic update checks.
    /// Default is 86400 (24 hours).
    var updateCheckInterval: TimeInterval {
        get { updaterController.updater.updateCheckInterval }
        set { updaterController.updater.updateCheckInterval = newValue }
    }

    /// The current app version (from Bundle).
    var currentVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0.0"
    }

    /// The current build number (from Bundle).
    var currentBuildNumber: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"
    }
}

// MARK: - SPUUpdaterDelegate

extension UpdateService: SPUUpdaterDelegate {
    /// Provides the appcast feed URL.
    ///
    /// This can be used to dynamically determine the feed URL at runtime.
    /// If nil is returned, Sparkle uses the `SUFeedURL` from Info.plist.
    nonisolated func feedURLString(for updater: SPUUpdater) -> String? {
        // Use Info.plist value by default, or override here if needed
        // Return nil to use SUFeedURL from Info.plist
        return "https://github.com/OximyHQ/mitmproxy/releases/latest/download/appcast.xml"
    }

    /// Called when Sparkle finds a valid update.
    nonisolated func updater(_ updater: SPUUpdater, didFindValidUpdate item: SUAppcastItem) {
        Task { @MainActor in
            self.updateAvailable = true
            self.latestVersion = item.displayVersionString
            self.lastError = nil

            print("[UpdateService] Update found: \(item.displayVersionString ?? "unknown") (build \(item.versionString))")

            // Log to Sentry for telemetry
            SentryService.shared.addStateBreadcrumb(
                category: "update",
                message: "Update available",
                data: [
                    "currentVersion": self.currentVersion,
                    "newVersion": item.displayVersionString ?? "unknown",
                    "newBuild": item.versionString
                ]
            )
        }
    }

    /// Called when Sparkle doesn't find an update (or encounters an error).
    nonisolated func updaterDidNotFindUpdate(_ updater: SPUUpdater, error: Error) {
        Task { @MainActor in
            self.updateAvailable = false
            self.latestVersion = nil
            self.lastError = error

            print("[UpdateService] No update found or error: \(error.localizedDescription)")
        }
    }

    /// Called when an update check is about to start.
    nonisolated func updater(_ updater: SPUUpdater, willDownloadUpdate item: SUAppcastItem, with request: NSMutableURLRequest) {
        print("[UpdateService] Downloading update: \(item.displayVersionString ?? "unknown")")
    }

    /// Called when an update was successfully downloaded.
    nonisolated func updater(_ updater: SPUUpdater, didDownloadUpdate item: SUAppcastItem) {
        print("[UpdateService] Download complete: \(item.displayVersionString ?? "unknown")")
    }

    /// Called when the updater will install an update.
    nonisolated func updater(_ updater: SPUUpdater, willInstallUpdate item: SUAppcastItem) {
        print("[UpdateService] Installing update: \(item.displayVersionString ?? "unknown")")

        // Log to Sentry
        Task { @MainActor in
            SentryService.shared.addStateBreadcrumb(
                category: "update",
                message: "Installing update",
                data: [
                    "version": item.displayVersionString ?? "unknown"
                ]
            )
        }
    }

    /// Called when the updater finishes installing an update and the app will relaunch.
    nonisolated func updater(_ updater: SPUUpdater, willRelaunchApplication item: SUAppcastItem) {
        print("[UpdateService] Relaunching after update to \(item.displayVersionString ?? "unknown")")
    }

    /// Called when the user cancels an update.
    nonisolated func userDidCancelDownload(_ updater: SPUUpdater) {
        print("[UpdateService] User cancelled update download")
    }
}

// MARK: - SPUStandardUserDriverDelegate

extension UpdateService: SPUStandardUserDriverDelegate {
    /// Whether to show gentle scheduled update reminders.
    ///
    /// When true, Sparkle shows less intrusive notifications for background updates.
    var supportsGentleScheduledUpdateReminders: Bool { true }

    /// Called before Sparkle shows its update UI.
    ///
    /// This can be used to customize behavior before the update dialog appears.
    nonisolated func standardUserDriverWillHandleShowingUpdate(
        _ handleShowingUpdate: Bool,
        forUpdate update: SUAppcastItem,
        state: SPUUserUpdateState
    ) {
        Task { @MainActor in
            self.isCheckingForUpdates = false

            if handleShowingUpdate {
                print("[UpdateService] Sparkle will show update UI for \(update.displayVersionString ?? "unknown")")
            }
        }
    }

    /// Called after Sparkle finishes showing its update UI.
    nonisolated func standardUserDriverDidReceiveUserAttention(forUpdate update: SUAppcastItem) {
        print("[UpdateService] User acknowledged update: \(update.displayVersionString ?? "unknown")")
    }
}
