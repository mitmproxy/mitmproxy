import Foundation
import SwiftUI

/// Global application state
@MainActor
final class AppState: ObservableObject {

    // MARK: - App Phase (simplified: setup or ready)

    enum Phase: String {
        case setup      // Needs cert + proxy
        case ready      // Monitoring active
    }

    @Published var phase: Phase = .setup {
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

    // MARK: - Account (stub for future)

    @Published var workspaceName: String = ""
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
    }

    // MARK: - State Management

    private func loadPersistedState() {
        let defaults = UserDefaults.standard

        // Check if setup was completed previously
        if defaults.bool(forKey: Constants.Defaults.setupComplete) {
            phase = .ready
        } else {
            phase = .setup
        }

        // Load account info if available
        if let workspace = defaults.string(forKey: Constants.Defaults.workspaceName) {
            workspaceName = workspace
            isLoggedIn = true
        }
    }

    /// Called when both cert and proxy are enabled
    func completeSetup() {
        UserDefaults.standard.set(true, forKey: Constants.Defaults.setupComplete)
        phase = .ready
        connectionStatus = .connected
    }

    /// Check if setup requirements are met
    var isSetupComplete: Bool {
        isCertificateInstalled && isProxyEnabled
    }

    /// Reset everything (for debugging/logout)
    func reset() {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.setupComplete)
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)

        phase = .setup
        connectionStatus = .disconnected
        workspaceName = ""
        isLoggedIn = false
        isCertificateInstalled = false
        isProxyEnabled = false
    }

    // MARK: - Account (stub)

    func login(workspaceName: String, deviceToken: String) {
        let defaults = UserDefaults.standard
        defaults.set(workspaceName, forKey: Constants.Defaults.workspaceName)
        defaults.set(deviceToken, forKey: Constants.Defaults.deviceToken)

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
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)

        // Clear Sentry user context
        SentryService.shared.clearUser()

        SentryService.shared.addStateBreadcrumb(
            category: "account",
            message: "User logged out"
        )

        workspaceName = ""
        isLoggedIn = false
    }
}
