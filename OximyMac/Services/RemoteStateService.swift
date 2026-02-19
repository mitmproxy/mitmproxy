import Foundation

/// Notification posted when sensor_enabled state changes
extension Notification.Name {
    static let sensorEnabledChanged = Notification.Name("sensorEnabledChanged")
    static let enforcementRulesChanged = Notification.Name("enforcementRulesChanged")
}

/// App-level feature flags from sensor-config API
struct AppConfigFlags: Codable {
    let disableUserLogout: Bool?
    let disableQuit: Bool?
    let forceAutoStart: Bool?
    let managedSetupComplete: Bool?
    let managedEnrollmentComplete: Bool?
    let managedCACertInstalled: Bool?
    let managedDeviceToken: String?
    let managedDeviceId: String?
    let managedWorkspaceId: String?
    let managedWorkspaceName: String?
    let apiEndpoint: String?
    let heartbeatInterval: Int?
}

/// Enforcement rule from the admin dashboard (via sensor-config → remote-state.json)
struct EnforcementRule: Codable, Equatable {
    let toolId: String
    let toolType: String         // "app" | "website"
    let displayName: String
    let mode: String             // "blocked" | "warn" | "flagged"
    let message: String?
    let conditions: String?
    let macBundleId: String?
    let windowsAppId: String?
    let domain: String?
    let exemptDeviceIds: [String]?  // Hardware IDs exempt from enforcement (approved access requests)
}

/// Remote state from Python addon (written to ~/.oximy/remote-state.json)
struct RemoteState: Codable {
    let sensorEnabled: Bool
    let forceLogout: Bool
    let proxyActive: Bool
    let tenantId: String?
    let itSupport: String?
    let timestamp: String
    let appConfig: AppConfigFlags?
    let enforcementRules: [EnforcementRule]?

    enum CodingKeys: String, CodingKey {
        case sensorEnabled = "sensor_enabled"
        case forceLogout = "force_logout"
        case proxyActive = "proxy_active"
        case tenantId
        case itSupport
        case timestamp
        case appConfig
        case enforcementRules
    }
}

/// Service that polls remote-state.json written by the Python addon
/// to reflect admin-controlled monitoring state in the Swift UI.
@MainActor
final class RemoteStateService: ObservableObject {
    static let shared = RemoteStateService()

    // MARK: - Published State

    @Published var sensorEnabled: Bool = true
    @Published var proxyActive: Bool = false
    @Published var tenantId: String?
    @Published var itSupport: String?
    @Published var lastUpdate: Date?
    @Published var isRunning = false
    @Published var appConfig: AppConfigFlags?
    @Published var enforcementRules: [EnforcementRule] = []

    // MARK: - Private

    private var timer: Timer?
    private static let pollInterval: TimeInterval = 2.0

    static var stateFilePath: URL {
        Constants.oximyDir.appendingPathComponent("remote-state.json")
    }

    private init() {
        // Read initial state
        readState()
    }

    // MARK: - Start/Stop

    func start() {
        guard !isRunning else { return }
        isRunning = true

        // Initial read
        readState()

        // Schedule recurring reads
        timer = Timer.scheduledTimer(withTimeInterval: Self.pollInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.readState()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isRunning = false
    }

    // MARK: - State Reading

    private func readState() {
        let fileURL = Self.stateFilePath

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            // File doesn't exist yet - addon may not have started
            // Keep current state (default is enabled)
            return
        }

        do {
            let data = try Data(contentsOf: fileURL)
            let decoder = JSONDecoder()
            let state = try decoder.decode(RemoteState.self, from: data)

            let previousEnabled = sensorEnabled

            sensorEnabled = state.sensorEnabled
            proxyActive = state.proxyActive
            tenantId = state.tenantId
            itSupport = state.itSupport
            appConfig = state.appConfig
            lastUpdate = Date()

            // Update enforcement rules and notify if changed
            let newRules = state.enforcementRules ?? []
            if newRules != enforcementRules {
                enforcementRules = newRules
                NotificationCenter.default.post(
                    name: .enforcementRulesChanged,
                    object: newRules
                )
            }

            // Handle state changes
            if previousEnabled != state.sensorEnabled {
                OximyLogger.shared.log(.STATE_STATE_001, "Sensor state changed", data: [
                    "sensor_enabled": state.sensorEnabled,
                    "previous": previousEnabled
                ])
                OximyLogger.shared.setTag("sensor_enabled", value: state.sensorEnabled ? "true" : "false")
                NotificationCenter.default.post(
                    name: .sensorEnabledChanged,
                    object: state.sensorEnabled
                )
            }

            // Handle force_logout command
            if state.forceLogout {
                handleForceLogout()
            }

        } catch {
            // Log but don't crash - file may be in process of being written
            print("[RemoteStateService] Failed to read state: \(error)")
            OximyLogger.shared.log(.STATE_FAIL_201, "Failed to read remote state file", data: [
                "error": error.localizedDescription
            ])
        }
    }

    private func handleForceLogout() {
        print("[RemoteStateService] Force logout command received")
        OximyLogger.shared.log(.STATE_CMD_003, "Force logout received")

        // Clear the force_logout flag by deleting the file
        // (addon will recreate it on next config fetch)
        try? FileManager.default.removeItem(at: Self.stateFilePath)

        // Trigger auth failure which returns to enrollment
        NotificationCenter.default.post(name: .authenticationFailed, object: nil)
    }
}
