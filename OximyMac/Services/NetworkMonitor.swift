import Foundation
import Network
import SystemConfiguration

/// Monitors network changes and triggers proxy reconfiguration
@MainActor
class NetworkMonitor: ObservableObject {
    static let shared = NetworkMonitor()

    @Published var isConnected = true
    @Published var currentInterfaces: [String] = []
    @Published var lastNetworkChange: Date?

    private var monitor: NWPathMonitor?
    private let queue = DispatchQueue(label: "com.oximy.networkmonitor")

    // Debounce rapid network changes
    private var debounceTask: Task<Void, Never>?
    private let debounceInterval: UInt64 = 1_000_000_000 // 1 second

    private init() {}

    // MARK: - Monitoring

    func startMonitoring() {
        guard monitor == nil else { return }

        monitor = NWPathMonitor()
        monitor?.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                self?.handlePathUpdate(path)
            }
        }
        monitor?.start(queue: queue)

        print("[NetworkMonitor] Started monitoring network changes")
    }

    func stopMonitoring() {
        monitor?.cancel()
        monitor = nil
        debounceTask?.cancel()
        print("[NetworkMonitor] Stopped monitoring")
    }

    // MARK: - Path Updates

    private func handlePathUpdate(_ path: NWPath) {
        let wasConnected = isConnected
        isConnected = path.status == .satisfied

        // Get current interface names
        let interfaces = path.availableInterfaces.map { $0.name }
        let interfacesChanged = Set(interfaces) != Set(currentInterfaces)

        // Log for debugging
        let interfaceTypes = path.availableInterfaces.map { iface -> String in
            switch iface.type {
            case .wifi: return "\(iface.name)(Wi-Fi)"
            case .wiredEthernet: return "\(iface.name)(Ethernet)"
            case .cellular: return "\(iface.name)(Cellular)"
            case .loopback: return "\(iface.name)(Loopback)"
            case .other: return "\(iface.name)(Other)"
            @unknown default: return "\(iface.name)(Unknown)"
            }
        }

        print("[NetworkMonitor] Path update: connected=\(isConnected), interfaces=\(interfaceTypes)")

        currentInterfaces = interfaces

        // Determine if we need to reconfigure
        let needsReconfigure = interfacesChanged || (isConnected && !wasConnected)

        if needsReconfigure {
            lastNetworkChange = Date()
            scheduleProxyReconfiguration()
        }
    }

    private func scheduleProxyReconfiguration() {
        // Cancel any pending reconfiguration
        debounceTask?.cancel()

        // Add breadcrumb for network change
        SentryService.shared.addStateBreadcrumb(
            category: "proxy",
            message: "Network changed - reconfiguring",
            data: ["interfaces": currentInterfaces]
        )

        // Debounce to avoid rapid reconfigurations
        debounceTask = Task {
            try? await Task.sleep(nanoseconds: debounceInterval)

            guard !Task.isCancelled else { return }

            print("[NetworkMonitor] Triggering proxy reconfiguration")
            NotificationCenter.default.post(name: .networkChanged, object: nil)
        }
    }

    // MARK: - Network Services

    /// Get all network service names (Wi-Fi, Ethernet, etc.)
    func getActiveNetworkServices() -> [String] {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/networksetup")
        process.arguments = ["-listallnetworkservices"]

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let output = String(data: data, encoding: .utf8) else { return ["Wi-Fi"] }

            return output.components(separatedBy: "\n")
                .dropFirst()  // Skip "An asterisk (*) denotes..." header
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty && !$0.hasPrefix("*") }
        } catch {
            print("[NetworkMonitor] Error getting network services: \(error)")
            return ["Wi-Fi"]  // Fallback
        }
    }

    /// Check if a specific interface type is available
    func hasInterfaceType(_ type: NWInterface.InterfaceType) -> Bool {
        guard monitor != nil else { return false }
        // Note: We can't directly query the monitor, so check currentInterfaces
        // This is a simplified check
        return isConnected
    }

    /// Get a human-readable description of current network
    var networkDescription: String {
        guard isConnected else { return "No Connection" }

        if currentInterfaces.contains(where: { $0.hasPrefix("en0") }) {
            return "Wi-Fi"
        } else if currentInterfaces.contains(where: { $0.hasPrefix("en") }) {
            return "Ethernet"
        } else if currentInterfaces.contains(where: { $0.hasPrefix("utun") }) {
            return "VPN"
        } else {
            return "Connected"
        }
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let networkChanged = Notification.Name("networkChanged")
    static let mitmproxyFailed = Notification.Name("mitmproxyFailed")
}
