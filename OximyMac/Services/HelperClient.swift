import Foundation

/// Client for communicating with the privileged helper
/// STUB: Real implementation requires SMJobBless and Developer ID signing
@MainActor
class HelperClient: ObservableObject {
    static let shared = HelperClient()

    @Published var isHelperInstalled = false
    @Published var lastError: String?

    private init() {
        checkHelperStatus()
    }

    // MARK: - Status

    /// Check if helper is installed
    func checkHelperStatus() {
        // STUB: In production, check if helper is registered with launchd
        // For now, always return false (helper not installed)
        isHelperInstalled = false
        print("[HelperClient] STUB: Helper not installed (requires Developer ID signing)")
    }

    // MARK: - Installation

    /// Install the privileged helper (requires password)
    func installHelper() async throws {
        // STUB: Real implementation uses SMJobBless
        print("[HelperClient] STUB: Would install privileged helper via SMJobBless")
        print("[HelperClient] STUB: This requires:")
        print("[HelperClient]   1. Developer ID Application certificate")
        print("[HelperClient]   2. Developer ID Installer certificate")
        print("[HelperClient]   3. Proper code signing setup in Xcode")
        print("[HelperClient]   4. Matching requirements in Info.plist")

        // Simulate installation for testing
        // In production, this would trigger a password prompt
        isHelperInstalled = true
        lastError = nil
    }

    /// Uninstall the privileged helper
    func uninstallHelper() async throws {
        // STUB: Remove helper from launchd
        print("[HelperClient] STUB: Would uninstall privileged helper")
        isHelperInstalled = false
    }

    // MARK: - Privileged Operations (Stubs)

    /// Enable proxy via privileged helper (no password prompt)
    func enableProxy(host: String, port: Int, services: [String]) async throws {
        if isHelperInstalled {
            // STUB: Would use XPC to communicate with helper
            print("[HelperClient] STUB: Would enable proxy via XPC to helper")
            print("[HelperClient] STUB: host=\(host), port=\(port), services=\(services)")
        } else {
            // Fallback to direct (will prompt for password)
            print("[HelperClient] Helper not installed, falling back to direct proxy config")
            try await ProxyService.shared.enableProxy(port: port)
        }
    }

    /// Disable proxy via privileged helper (no password prompt)
    func disableProxy(services: [String]) async throws {
        if isHelperInstalled {
            // STUB: Would use XPC to communicate with helper
            print("[HelperClient] STUB: Would disable proxy via XPC to helper")
        } else {
            // Fallback to direct
            print("[HelperClient] Helper not installed, falling back to direct proxy config")
            try await ProxyService.shared.disableProxy()
        }
    }

    /// Install certificate via privileged helper (no password prompt)
    func installCertificate(atPath path: String) async throws {
        if isHelperInstalled {
            // STUB: Would use XPC to install cert to System keychain
            print("[HelperClient] STUB: Would install certificate via XPC to helper")
            print("[HelperClient] STUB: path=\(path)")
        } else {
            // Fallback to direct (will prompt for password)
            print("[HelperClient] Helper not installed, user must install cert manually")
            throw HelperClientError.helperNotInstalled
        }
    }

    /// Remove certificate via privileged helper
    func removeCertificate(named name: String) async throws {
        if isHelperInstalled {
            print("[HelperClient] STUB: Would remove certificate '\(name)' via XPC to helper")
        } else {
            throw HelperClientError.helperNotInstalled
        }
    }
}

// MARK: - Errors

enum HelperClientError: LocalizedError {
    case helperNotInstalled
    case communicationFailed(String)
    case operationFailed(String)

    var errorDescription: String? {
        switch self {
        case .helperNotInstalled:
            return "Privileged helper not installed. Operation requires password."
        case .communicationFailed(let reason):
            return "Failed to communicate with helper: \(reason)"
        case .operationFailed(let reason):
            return "Helper operation failed: \(reason)"
        }
    }
}

// MARK: - Helper Protocol (for future XPC implementation)

/// Protocol defining privileged operations
/// In production, this would be shared between main app and helper
protocol HelperProtocol {
    func enableProxy(host: String, port: Int, services: [String],
                     completion: @escaping (Bool, String?) -> Void)

    func disableProxy(services: [String],
                      completion: @escaping (Bool, String?) -> Void)

    func installCertificate(atPath: String,
                            completion: @escaping (Bool, String?) -> Void)

    func removeCertificate(named: String,
                           completion: @escaping (Bool, String?) -> Void)
}
