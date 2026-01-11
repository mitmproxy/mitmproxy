import Foundation

/// Service to manage system proxy configuration
@MainActor
class ProxyService: ObservableObject {
    static let shared = ProxyService()

    @Published var isProxyEnabled = false
    @Published var configuredPort: Int?
    @Published var lastError: String?

    private init() {
        checkStatus()
    }

    // MARK: - Status Check

    /// Check if proxy is currently enabled
    func checkStatus() {
        // Check Wi-Fi proxy settings
        if let (enabled, port) = getProxySettings(for: "Wi-Fi") {
            isProxyEnabled = enabled
            configuredPort = enabled ? port : nil
            return
        }

        // Check Ethernet as fallback
        if let (enabled, port) = getProxySettings(for: "Ethernet") {
            isProxyEnabled = enabled
            configuredPort = enabled ? port : nil
            return
        }

        isProxyEnabled = false
        configuredPort = nil
    }

    /// Get current proxy settings for a network service
    private func getProxySettings(for service: String) -> (enabled: Bool, port: Int)? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/networksetup")
        process.arguments = ["-getsecurewebproxy", service]

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let output = String(data: data, encoding: .utf8) else { return nil }

            // Parse output like:
            // Enabled: Yes
            // Server: 127.0.0.1
            // Port: 1030
            let lines = output.components(separatedBy: "\n")
            var enabled = false
            var port = 0

            for line in lines {
                if line.contains("Enabled:") {
                    enabled = line.contains("Yes")
                } else if line.contains("Port:") {
                    let parts = line.components(separatedBy: ":")
                    if parts.count >= 2, let p = Int(parts[1].trimmingCharacters(in: .whitespaces)) {
                        port = p
                    }
                }
            }

            return (enabled, port)
        } catch {
            return nil
        }
    }

    // MARK: - Enable Proxy

    /// Enable system proxy on all network interfaces
    func enableProxy(port: Int) async throws {
        let services = getNetworkServices()

        do {
            for service in services {
                try await setProxy(enabled: true, port: port, for: service)
            }

            isProxyEnabled = true
            configuredPort = port
            lastError = nil
            print("[ProxyService] Enabled proxy on port \(port)")

            SentryService.shared.addStateBreadcrumb(
                category: "proxy",
                message: "Proxy enabled",
                data: ["port": port, "services": services]
            )
        } catch {
            SentryService.shared.captureError(error, context: [
                "operation": "proxy_enable",
                "port": port,
                "services": services
            ])
            throw error
        }
    }

    /// Get list of network services
    private func getNetworkServices() -> [String] {
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

            // Parse output - skip first line which is a header
            let lines = output.components(separatedBy: "\n")
                .dropFirst()
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty && !$0.hasPrefix("*") }

            return Array(lines)
        } catch {
            return ["Wi-Fi"]  // Fallback
        }
    }

    /// Set proxy for a specific network service
    private func setProxy(enabled: Bool, port: Int, for service: String) async throws {
        let host = Constants.listenHost

        if enabled {
            // Set HTTP proxy
            try await runNetworkSetup(["-setwebproxy", service, host, String(port)])
            try await runNetworkSetup(["-setwebproxystate", service, "on"])

            // Set HTTPS proxy
            try await runNetworkSetup(["-setsecurewebproxy", service, host, String(port)])
            try await runNetworkSetup(["-setsecurewebproxystate", service, "on"])
        } else {
            // Disable HTTP proxy
            try await runNetworkSetup(["-setwebproxystate", service, "off"])

            // Disable HTTPS proxy
            try await runNetworkSetup(["-setsecurewebproxystate", service, "off"])
        }
    }

    /// Run networksetup command
    private func runNetworkSetup(_ arguments: [String]) async throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/networksetup")
        process.arguments = arguments

        let errorPipe = Pipe()
        process.standardError = errorPipe
        process.standardOutput = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()

            if process.terminationStatus != 0 {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
                // Don't throw for minor errors (like service not found)
                print("[ProxyService] Warning: \(errorMessage)")
            }
        } catch {
            throw ProxyError.commandFailed(error.localizedDescription)
        }
    }

    // MARK: - Disable Proxy

    /// Disable system proxy on all network interfaces
    func disableProxy() async throws {
        let services = getNetworkServices()

        do {
            for service in services {
                try await setProxy(enabled: false, port: 0, for: service)
            }

            isProxyEnabled = false
            configuredPort = nil
            lastError = nil
            print("[ProxyService] Disabled proxy")

            SentryService.shared.addStateBreadcrumb(
                category: "proxy",
                message: "Proxy disabled"
            )
        } catch {
            SentryService.shared.captureError(error, context: [
                "operation": "proxy_disable",
                "services": services
            ])
            throw error
        }
    }

    /// Synchronous version for cleanup on app termination
    /// This ensures proxy is disabled even if app is force-quit
    func disableProxySync() {
        let services = getNetworkServices()

        for service in services {
            // Disable HTTP proxy
            runNetworkSetupSync(["-setwebproxystate", service, "off"])
            // Disable HTTPS proxy
            runNetworkSetupSync(["-setsecurewebproxystate", service, "off"])
        }

        isProxyEnabled = false
        configuredPort = nil
        print("[ProxyService] Disabled proxy (sync)")
    }

    /// Synchronous networksetup for cleanup
    private func runNetworkSetupSync(_ arguments: [String]) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/networksetup")
        process.arguments = arguments
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            print("[ProxyService] Sync cleanup error: \(error)")
        }
    }

    // MARK: - Bypass List

    /// Set proxy bypass list (domains that should not go through proxy)
    func setBypassList(_ domains: [String]) async throws {
        let services = getNetworkServices()
        let bypassList = domains.joined(separator: " ")

        for service in services {
            try await runNetworkSetup(["-setproxybypassdomains", service, bypassList])
        }
    }

    /// Get default bypass list
    static var defaultBypassList: [String] {
        [
            "localhost",
            "127.0.0.1",
            "*.local",
            "169.254/16"
        ]
    }
}

// MARK: - Errors

enum ProxyError: LocalizedError {
    case commandFailed(String)
    case serviceNotFound(String)

    var errorDescription: String? {
        switch self {
        case .commandFailed(let reason):
            return "Proxy configuration failed: \(reason)"
        case .serviceNotFound(let service):
            return "Network service not found: \(service)"
        }
    }
}
