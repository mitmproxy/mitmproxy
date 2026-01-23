import Foundation
import SwiftUI

/// Global application state
@MainActor
final class AppState: ObservableObject {

    // MARK: - App Phase
    // Flow: enrollment → setup → ready

    enum Phase: String {
        case enrollment // Step 1: Connect to workspace (6-digit code)
        case setup      // Step 2: Install cert + enable proxy
        case ready      // Done: Monitoring active
    }

    @Published var phase: Phase = .enrollment {
        didSet {
            guard oldValue != phase else { return }
            SentryService.shared.addStateBreadcrumb(
                category: "app.phase",
                message: "Phase changed",
                data: ["from": oldValue.rawValue, "to": phase.rawValue]
            )
            SentryService.shared.updateContext(
                phase: phase.rawValue,
                proxyEnabled: isProxyEnabled,
                port: currentPort
            )
        }
    }

    // MARK: - Connection Status

    enum ConnectionStatus {
        case disconnected
        case connecting
        case connected
        case error(String)

        var color: Color {
            switch self {
            case .disconnected: return .gray
            case .connecting: return .orange
            case .connected: return .green
            case .error: return .red
            }
        }

        var label: String {
            switch self {
            case .disconnected: return "Disconnected"
            case .connecting: return "Connecting..."
            case .connected: return "Monitoring Active"
            case .error(let msg): return msg
            }
        }

        var isConnected: Bool {
            if case .connected = self { return true }
            return false
        }
    }

    @Published var connectionStatus: ConnectionStatus = .disconnected

    // MARK: - Permissions Status

    @Published var isCertificateInstalled: Bool = false
    @Published var isProxyEnabled: Bool = false

    // MARK: - Stats

    @Published var eventsCapturedToday: Int = 0
    @Published var currentPort: Int = Constants.preferredPort

    // MARK: - Account

    @Published var workspaceName: String = ""
    @Published var deviceId: String = ""
    @Published var isLoggedIn: Bool = false

    // MARK: - Main Tabs

    enum MainTab: String, CaseIterable {
        case home = "Home"
        case settings = "Settings"
        case support = "Support"

        var icon: String {
            switch self {
            case .home: return "house.fill"
            case .settings: return "gearshape.fill"
            case .support: return "questionmark.circle.fill"
            }
        }
    }

    @Published var selectedTab: MainTab = .home

    // MARK: - Device Info

    var deviceName: String {
        Host.current().localizedName ?? "Mac"
    }

    // MARK: - Initialization

    init() {
        loadPersistedState()
        setupNotificationObservers()
    }

    private func setupNotificationObservers() {
        NotificationCenter.default.addObserver(
            forName: .workspaceNameUpdated,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            if let newName = notification.object as? String {
                self?.workspaceName = newName
            }
        }
    }

    // MARK: - State Management

    private func loadPersistedState() {
        let defaults = UserDefaults.standard

        // Load account info if available
        if let workspace = defaults.string(forKey: Constants.Defaults.workspaceName) {
            workspaceName = workspace
            isLoggedIn = true
        }
        if let device = defaults.string(forKey: Constants.Defaults.deviceId) {
            deviceId = device
        }

        // Determine phase based on what's been completed
        let hasDeviceToken = defaults.string(forKey: Constants.Defaults.deviceToken) != nil
        let setupComplete = defaults.bool(forKey: Constants.Defaults.setupComplete)

        // Ensure device token file exists (handles upgrade from older versions)
        if hasDeviceToken {
            ensureDeviceTokenFile()
        }

        if hasDeviceToken && setupComplete {
            // Both enrollment and setup done
            phase = .ready
            startServices()
        } else if hasDeviceToken {
            // Enrolled but setup not complete
            phase = .setup
        } else {
            // Fresh install - start with enrollment
            phase = .enrollment
        }
    }

    // MARK: - Phase Transitions

    /// Called after successful enrollment (step 1 complete)
    func completeEnrollment() {
        // Move to setup phase
        phase = .setup
    }

    /// Called when both cert and proxy are enabled (step 2 complete)
    func completeSetup() {
        UserDefaults.standard.set(true, forKey: Constants.Defaults.setupComplete)
        phase = .ready
        connectionStatus = .connected
        startServices()
    }

    /// Go back to enrollment from setup
    func goBackToEnrollment() {
        phase = .enrollment
    }

    /// Skip setup and go to ready state without enabling proxy
    func skipSetup() {
        UserDefaults.standard.set(true, forKey: Constants.Defaults.setupComplete)
        phase = .ready
        connectionStatus = .disconnected
        startServices()
    }

    /// Handle auth failure after retries exhausted
    func handleAuthFailure() {
        logout()
    }

    /// Start background services
    private func startServices() {
        HeartbeatService.shared.start()
        SyncService.shared.start()
    }

    /// Stop background services
    private func stopServices() {
        HeartbeatService.shared.stop()
        SyncService.shared.stop()
    }

    /// Check if setup requirements are met
    var isSetupComplete: Bool {
        isCertificateInstalled && isProxyEnabled
    }

    /// Reset everything (for debugging/logout)
    func reset() {
        stopServices()

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.setupComplete)
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)
        defaults.removeObject(forKey: Constants.Defaults.deviceId)
        defaults.removeObject(forKey: Constants.Defaults.workspaceId)

        // Delete device token file
        deleteDeviceTokenFile()

        phase = .enrollment
        connectionStatus = .disconnected
        workspaceName = ""
        deviceId = ""
        isLoggedIn = false
        isCertificateInstalled = false
        isProxyEnabled = false
    }

    // MARK: - Device Token File Management

    /// Write device token to ~/.oximy/device-token for the Python addon
    @discardableResult
    private func writeDeviceTokenFile(_ token: String) -> Bool {
        let tokenPath = Constants.deviceTokenPath
        let oximyDir = Constants.oximyDir
        let fm = FileManager.default

        do {
            // Ensure ~/.oximy directory exists
            if !fm.fileExists(atPath: oximyDir.path) {
                try fm.createDirectory(at: oximyDir, withIntermediateDirectories: true)
            }

            // Write token as plain text (addon uses .strip() on read)
            try token.write(to: tokenPath, atomically: true, encoding: .utf8)

            // Set file permissions to owner-only readable (0600) for security
            try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: tokenPath.path)

            print("[AppState] Device token written to \(tokenPath.path)")
            return true
        } catch {
            print("[AppState] Failed to write device token file: \(error.localizedDescription)")
            SentryService.shared.captureError(error, context: [
                "operation": "write_device_token",
                "path": tokenPath.path
            ])
            return false
        }
    }

    /// Delete the device token file on logout/reset
    @discardableResult
    private func deleteDeviceTokenFile() -> Bool {
        let tokenPath = Constants.deviceTokenPath
        let fm = FileManager.default

        guard fm.fileExists(atPath: tokenPath.path) else {
            return true  // File doesn't exist, nothing to delete
        }

        do {
            try fm.removeItem(at: tokenPath)
            print("[AppState] Device token file deleted")
            return true
        } catch {
            print("[AppState] Failed to delete device token file: \(error.localizedDescription)")
            SentryService.shared.captureError(error, context: [
                "operation": "delete_device_token",
                "path": tokenPath.path
            ])
            return false
        }
    }

    /// Ensure device token file exists if we have a token (handles app upgrades)
    private func ensureDeviceTokenFile() {
        guard let token = UserDefaults.standard.string(forKey: Constants.Defaults.deviceToken),
              !token.isEmpty else {
            return
        }

        let tokenPath = Constants.deviceTokenPath
        let fm = FileManager.default

        // Check if file already exists with correct content
        if fm.fileExists(atPath: tokenPath.path),
           let existingToken = try? String(contentsOf: tokenPath, encoding: .utf8),
           existingToken.trimmingCharacters(in: .whitespacesAndNewlines) == token {
            return  // File exists with correct content
        }

        // File missing or has stale content - write it
        writeDeviceTokenFile(token)
    }

    // MARK: - Account

    func login(workspaceName: String, deviceToken: String, deviceId: String?, workspaceId: String?) {
        let defaults = UserDefaults.standard
        defaults.set(workspaceName, forKey: Constants.Defaults.workspaceName)
        defaults.set(deviceToken, forKey: Constants.Defaults.deviceToken)

        // Write token to file for Python addon
        writeDeviceTokenFile(deviceToken)

        if let deviceId = deviceId {
            defaults.set(deviceId, forKey: Constants.Defaults.deviceId)
            self.deviceId = deviceId
        }

        if let workspaceId = workspaceId {
            defaults.set(workspaceId, forKey: Constants.Defaults.workspaceId)
        }

        self.workspaceName = workspaceName
        self.isLoggedIn = true

        // Update Sentry user context
        SentryService.shared.setUser(workspaceName: workspaceName)

        SentryService.shared.addStateBreadcrumb(
            category: "account",
            message: "User logged in",
            data: ["workspace": workspaceName]
        )
    }

    func logout() {
        // Stop services first
        stopServices()

        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)
        defaults.removeObject(forKey: Constants.Defaults.deviceId)
        defaults.removeObject(forKey: Constants.Defaults.workspaceId)
        defaults.removeObject(forKey: Constants.Defaults.setupComplete)

        // Delete device token file
        deleteDeviceTokenFile()

        // Clear Sentry user context
        SentryService.shared.clearUser()

        SentryService.shared.addStateBreadcrumb(
            category: "account",
            message: "User logged out"
        )

        workspaceName = ""
        deviceId = ""
        isLoggedIn = false

        // Return to enrollment (step 1)
        phase = .enrollment
    }
}
