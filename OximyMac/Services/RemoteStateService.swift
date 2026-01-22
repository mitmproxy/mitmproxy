import Foundation

/// Notification posted when sensor_enabled state changes
extension Notification.Name {
    static let sensorEnabledChanged = Notification.Name("sensorEnabledChanged")
}

/// Remote state from Python addon (written to ~/.oximy/remote-state.json)
struct RemoteState: Codable {
    let sensorEnabled: Bool
    let forceLogout: Bool
    let proxyActive: Bool
    let tenantId: String?
    let itSupport: String?
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case sensorEnabled = "sensor_enabled"
        case forceLogout = "force_logout"
        case proxyActive = "proxy_active"
        case tenantId
        case itSupport
        case timestamp
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
            lastUpdate = Date()

            // Handle state changes
            if previousEnabled != state.sensorEnabled {
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
        }
    }

    private func handleForceLogout() {
        print("[RemoteStateService] Force logout command received")

        // Clear the force_logout flag by deleting the file
        // (addon will recreate it on next config fetch)
        try? FileManager.default.removeItem(at: Self.stateFilePath)

        // Trigger auth failure which returns to enrollment
        NotificationCenter.default.post(name: .authenticationFailed, object: nil)
    }
}
