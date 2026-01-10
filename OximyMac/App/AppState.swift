import Foundation
import SwiftUI

/// Global application state managed as an ObservableObject
@MainActor
final class AppState: ObservableObject {

    // MARK: - App Phase

    enum Phase: String, CaseIterable {
        case onboarding
        case permissions
        case login
        case connected
    }

    @Published var phase: Phase = .onboarding

    // MARK: - Connection Status

    enum ConnectionStatus {
        case disconnected
        case connecting
        case connected
        case error(String)

        var color: Color {
            switch self {
            case .disconnected: return .gray
            case .connecting: return .yellow
            case .connected: return .green
            case .error: return .red
            }
        }

        var label: String {
            switch self {
            case .disconnected: return "Disconnected"
            case .connecting: return "Connecting..."
            case .connected: return "Connected"
            case .error(let msg): return "Error: \(msg)"
            }
        }
    }

    @Published var connectionStatus: ConnectionStatus = .disconnected

    // MARK: - Device & Workspace

    @Published var deviceName: String = Host.current().localizedName ?? "Unknown Device"
    @Published var workspaceName: String = ""

    // MARK: - Permissions Status

    @Published var isCertificateInstalled: Bool = false
    @Published var isProxyEnabled: Bool = false

    // MARK: - Stats

    @Published var eventsCapturedToday: Int = 0
    @Published var currentPort: Int = Constants.preferredPort

    // MARK: - Initialization

    init() {
        loadPersistedState()
    }

    // MARK: - Persistence

    private func loadPersistedState() {
        let defaults = UserDefaults.standard

        // Check if onboarding is complete
        if defaults.bool(forKey: Constants.Defaults.onboardingComplete) {
            // Check if we have a device token (logged in)
            if let _ = defaults.string(forKey: Constants.Defaults.deviceToken),
               let workspace = defaults.string(forKey: Constants.Defaults.workspaceName) {
                workspaceName = workspace
                phase = .connected
            } else {
                phase = .login
            }
        } else {
            phase = .onboarding
        }
    }

    func completeOnboarding() {
        UserDefaults.standard.set(true, forKey: Constants.Defaults.onboardingComplete)
        phase = .permissions
    }

    func completePermissions() {
        phase = .login
    }

    func completeLogin(workspaceName: String, deviceToken: String) {
        let defaults = UserDefaults.standard
        defaults.set(workspaceName, forKey: Constants.Defaults.workspaceName)
        defaults.set(deviceToken, forKey: Constants.Defaults.deviceToken)

        self.workspaceName = workspaceName
        phase = .connected
    }

    func logout() {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)

        workspaceName = ""
        phase = .login
    }

    func resetOnboarding() {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.onboardingComplete)
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)
        defaults.removeObject(forKey: Constants.Defaults.workspaceName)

        workspaceName = ""
        phase = .onboarding
    }
}
