import Foundation

/// Notification posted when sensor_enabled state changes
extension Notification.Name {
    static let sensorEnabledChanged = Notification.Name("sensorEnabledChanged")
    static let enforcementRulesChanged = Notification.Name("enforcementRulesChanged")
    static let uninstallCertificateChanged = Notification.Name("uninstallCertificateChanged")
}

/// App-level feature flags from sensor-config API
struct AppConfigFlags: Codable {
    let disableUserLogout: Bool?
    let disableQuit: Bool?
    let forceAutoStart: Bool?
    let uninstallCertificate: Bool?
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
    let eventsPending: Int?

    enum CodingKeys: String, CodingKey {
        case sensorEnabled = "sensor_enabled"
        case forceLogout = "force_logout"
        case proxyActive = "proxy_active"
        case tenantId
        case itSupport
        case timestamp
        case appConfig
        case enforcementRules
        case eventsPending = "events_pending"
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
    @Published var eventsPending: Int = 0
    /// Tracks the last uninstallCertificate value read from the FILE only.
    /// Heartbeat updates do NOT modify this — preventing stale file data from
    /// generating spurious change notifications after a heartbeat override.
    private var lastFileUninstallCert: Bool?
    /// Tracks the file's timestamp to detect stale re-reads.
    /// When the file hasn't changed, we skip overwriting appConfig
    /// so heartbeat-delivered values aren't clobbered by stale data.
    private var lastFileTimestamp: String?

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

            let isNewFileData = state.timestamp != lastFileTimestamp
            lastFileTimestamp = state.timestamp

            let previousEnabled = sensorEnabled

            sensorEnabled = state.sensorEnabled
            proxyActive = state.proxyActive
            tenantId = state.tenantId
            itSupport = state.itSupport
            eventsPending = state.eventsPending ?? 0
            lastUpdate = Date()

            // Only update appConfig from file when the file has new data.
            // This prevents stale file reads from overwriting heartbeat-delivered values.
            if isNewFileData {
                appConfig = state.appConfig
            }

            // Update enforcement rules and notify if changed
            let newRules = state.enforcementRules ?? []
            if newRules != enforcementRules {
                enforcementRules = newRules
                NotificationCenter.default.post(
                    name: .enforcementRulesChanged,
                    object: newRules
                )
            }

            // Detect uninstallCertificate transition in FILE data only.
            // Only process when file has new data — stale reads skip entirely.
            if isNewFileData {
                let newUninstallCert = state.appConfig?.uninstallCertificate ?? false
                if lastFileUninstallCert != nil && newUninstallCert != lastFileUninstallCert {
                    NotificationCenter.default.post(
                        name: .uninstallCertificateChanged,
                        object: newUninstallCert
                    )
                }
                lastFileUninstallCert = newUninstallCert
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

    // MARK: - External Updates

    /// Accept appConfig updates from sources other than remote-state.json (e.g. heartbeat).
    /// This ensures certificate reinstall commands are received even when mitmproxy is stopped.
    func updateAppConfig(_ config: AppConfigFlags) {
        appConfig = config

        // Fire notification if heartbeat value differs from last file value.
        // Do NOT update lastFileUninstallCert — only readState() writes that,
        // so stale file reads always compare against themselves.
        let newUninstallCert = config.uninstallCertificate ?? false
        let currentFileValue = lastFileUninstallCert ?? false
        if newUninstallCert != currentFileValue {
            NotificationCenter.default.post(
                name: .uninstallCertificateChanged,
                object: newUninstallCert
            )
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
