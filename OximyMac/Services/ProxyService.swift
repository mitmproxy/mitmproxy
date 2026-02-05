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

    // MARK: - Startup Cleanup

    /// Clean up orphaned proxy settings on app launch
    /// FAIL-OPEN: This handles the case where the app crashed with proxy enabled,
    /// leaving the system proxy pointing to a dead port (blocking all traffic).
    func cleanupOrphanedProxy() {
        // Check all network services for orphaned proxies
        let services = getNetworkServices()

        for service in services {
            if let (enabled, port) = getProxySettings(for: service), enabled {
                // Proxy is enabled - check if it's pointing to a dead port
                if !isPortListening(port) {
                    // FAIL-OPEN: Proxy is pointing to dead port - clear it immediately
                    NSLog("[ProxyService] FAIL-OPEN: Found orphaned proxy on %@ pointing to dead port %d - cleaning up", service, port)
                    disableProxySync()

                    SentryService.shared.addStateBreadcrumb(
                        category: "proxy",
                        message: "FAIL-OPEN: Cleaned up orphaned proxy pointing to dead port",
                        data: ["service": service, "dead_port": port]
                    )
                    return  // Already cleaned up all services
                } else {
                    // Port is listening - might be another proxy instance, log but don't clean
                    NSLog("[ProxyService] Proxy on %@ port %d is active (something is listening)", service, port)
                }
            }
        }
    }

    /// Check if something is listening on a port
    private func isPortListening(_ port: Int) -> Bool {
        let socketFD = socket(AF_INET, SOCK_STREAM, 0)
        guard socketFD >= 0 else { return false }
        defer { close(socketFD) }

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(port).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")

        let connectResult = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPtr in
                connect(socketFD, sockaddrPtr, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        return connectResult == 0
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

    /// Run networksetup command (async version with error reporting)
    private func runNetworkSetup(_ arguments: [String]) async throws {
        let result = executeNetworkSetup(arguments, captureErrors: true)

        if let errorMessage = result.errorMessage {
            // Log warning to Sentry for visibility
            SentryService.shared.addErrorBreadcrumb(
                service: "proxy",
                error: "networksetup warning: \(errorMessage)"
            )

            // Update lastError so UI can show it (but don't throw for minor errors)
            lastError = "Proxy warning: \(errorMessage.trimmingCharacters(in: .whitespacesAndNewlines))"
            NSLog("[ProxyService] Warning: %@", errorMessage)
        }

        if let launchError = result.launchError {
            throw ProxyError.commandFailed(launchError)
        }
    }

    /// Core networksetup execution - shared between async and sync versions
    private struct NetworkSetupResult {
        let exitCode: Int32
        let errorMessage: String?
        let launchError: String?
    }

    private func executeNetworkSetup(_ arguments: [String], captureErrors: Bool) -> NetworkSetupResult {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/networksetup")
        process.arguments = arguments
        process.standardOutput = FileHandle.nullDevice

        var errorPipe: Pipe?
        if captureErrors {
            errorPipe = Pipe()
            process.standardError = errorPipe
        } else {
            process.standardError = FileHandle.nullDevice
        }

        do {
            try process.run()
            process.waitUntilExit()

            var errorMessage: String?
            if process.terminationStatus != 0, let pipe = errorPipe {
                let errorData = pipe.fileHandleForReading.readDataToEndOfFile()
                errorMessage = String(data: errorData, encoding: .utf8)
            }

            return NetworkSetupResult(
                exitCode: process.terminationStatus,
                errorMessage: errorMessage,
                launchError: nil
            )
        } catch {
            return NetworkSetupResult(
                exitCode: -1,
                errorMessage: nil,
                launchError: error.localizedDescription
            )
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
            // Disable HTTP proxy - use shared executor without error capture for speed
            _ = executeNetworkSetup(["-setwebproxystate", service, "off"], captureErrors: false)
            // Disable HTTPS proxy
            _ = executeNetworkSetup(["-setsecurewebproxystate", service, "off"], captureErrors: false)
        }

        isProxyEnabled = false
        configuredPort = nil
        print("[ProxyService] Disabled proxy (sync)")
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
