import Foundation
import Security

/// Service to manage CA certificate generation and Keychain installation
@MainActor
class CertificateService: ObservableObject {
    static let shared = CertificateService()

    @Published var isCAGenerated = false
    @Published var isCAInstalled = false
    @Published var lastError: String?

    private init() {
        checkStatus()
    }

    // MARK: - Status Check

    /// Check current CA status
    func checkStatus() {
        isCAGenerated = FileManager.default.fileExists(atPath: Constants.caCertPath.path)
        isCAInstalled = isCAInKeychain()
    }

    /// Check if Oximy CA is in the Keychain
    private func isCAInKeychain() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassCertificate,
            kSecAttrLabel as String: Constants.caCommonName,
            kSecReturnRef as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        return status == errSecSuccess
    }

    // MARK: - CA Generation

    /// Generate Oximy-branded CA certificate using OpenSSL
    func generateCA() async throws {
        // Ensure directory exists
        let fm = FileManager.default
        if !fm.fileExists(atPath: Constants.oximyDir.path) {
            try fm.createDirectory(at: Constants.oximyDir, withIntermediateDirectories: true)
        }

        // Skip if already exists
        if fm.fileExists(atPath: Constants.caCertPath.path) &&
           fm.fileExists(atPath: Constants.caKeyPath.path) {
            isCAGenerated = true
            return
        }

        // Generate CA using OpenSSL
        // This creates both the private key and certificate
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/openssl")
        process.arguments = [
            "req", "-x509", "-new", "-nodes",
            "-newkey", "rsa:4096",
            "-keyout", Constants.caKeyPath.path,
            "-out", Constants.caCertPath.path,
            "-days", String(Constants.caValidityDays),
            "-subj", "/CN=\(Constants.caCommonName)/O=\(Constants.caOrganization)/C=\(Constants.caCountry)"
        ]

        let errorPipe = Pipe()
        process.standardError = errorPipe
        process.standardOutput = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()

            if process.terminationStatus != 0 {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
                throw CertificateError.generationFailed(errorMessage)
            }

            // Also create a PKCS12 version for easier import
            try await createPKCS12()

            isCAGenerated = true
            lastError = nil
            print("[CertificateService] CA generated successfully")

        } catch {
            lastError = error.localizedDescription
            throw error
        }
    }

    /// Create PKCS12 file for Keychain import
    private func createPKCS12() async throws {
        let p12Path = Constants.oximyDir.appendingPathComponent("mitmproxy-ca.p12")

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/openssl")
        process.arguments = [
            "pkcs12", "-export",
            "-inkey", Constants.caKeyPath.path,
            "-in", Constants.caCertPath.path,
            "-out", p12Path.path,
            "-passout", "pass:"  // No password
        ]

        try process.run()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            throw CertificateError.pkcs12Failed
        }
    }

    // MARK: - Keychain Installation

    /// Install CA certificate to Keychain with trust settings
    /// This will prompt the user for their password
    func installCA() async throws {
        if !isCAGenerated {
            try await generateCA()
        }

        // Method 1: Use security command to add and trust the certificate
        // This triggers the standard macOS password prompt
        try await addCertToKeychain()
        try await trustCertInKeychain()

        isCAInstalled = true
        lastError = nil
        print("[CertificateService] CA installed to Keychain")
    }

    /// Add certificate to Keychain using security command
    private func addCertToKeychain() async throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/security")
        process.arguments = [
            "add-trusted-cert",
            "-d",  // Add to admin cert store
            "-r", "trustRoot",  // Trust as root CA
            "-k", "/Library/Keychains/System.keychain",
            Constants.caCertPath.path
        ]

        let errorPipe = Pipe()
        process.standardError = errorPipe
        process.standardOutput = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()

            // Status 0 = success, but non-zero might just mean it needs admin auth
            if process.terminationStatus != 0 {
                // Try user keychain instead (doesn't require admin)
                try await addCertToUserKeychain()
            }
        } catch {
            throw CertificateError.keychainAddFailed(error.localizedDescription)
        }
    }

    /// Add certificate to user's login keychain (fallback)
    private func addCertToUserKeychain() async throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/security")
        process.arguments = [
            "add-trusted-cert",
            "-r", "trustRoot",
            "-k", "\(NSHomeDirectory())/Library/Keychains/login.keychain-db",
            Constants.caCertPath.path
        ]

        try process.run()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            throw CertificateError.keychainAddFailed("Could not add certificate to keychain")
        }
    }

    /// Set trust settings for the certificate
    private func trustCertInKeychain() async throws {
        // The add-trusted-cert with -r trustRoot should handle this,
        // but we can also explicitly set trust settings
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/security")
        process.arguments = [
            "add-trusted-cert",
            "-r", "trustRoot",
            "-p", "ssl",
            Constants.caCertPath.path
        ]

        // This might prompt for password
        try process.run()
        process.waitUntilExit()
        // Ignore exit status - the certificate might already be trusted
    }

    // MARK: - Removal

    /// Remove CA certificate from Keychain
    func removeCA() async throws {
        // Find and delete the certificate
        let query: [String: Any] = [
            kSecClass as String: kSecClassCertificate,
            kSecAttrLabel as String: Constants.caCommonName
        ]

        let status = SecItemDelete(query as CFDictionary)
        if status != errSecSuccess && status != errSecItemNotFound {
            throw CertificateError.removalFailed
        }

        isCAInstalled = false
        print("[CertificateService] CA removed from Keychain")
    }

    /// Delete CA files from disk
    func deleteCAFiles() throws {
        let fm = FileManager.default

        if fm.fileExists(atPath: Constants.caCertPath.path) {
            try fm.removeItem(at: Constants.caCertPath)
        }

        if fm.fileExists(atPath: Constants.caKeyPath.path) {
            try fm.removeItem(at: Constants.caKeyPath)
        }

        let p12Path = Constants.oximyDir.appendingPathComponent("mitmproxy-ca.p12")
        if fm.fileExists(atPath: p12Path.path) {
            try fm.removeItem(at: p12Path)
        }

        isCAGenerated = false
        print("[CertificateService] CA files deleted")
    }
}

// MARK: - Errors

enum CertificateError: LocalizedError {
    case generationFailed(String)
    case pkcs12Failed
    case keychainAddFailed(String)
    case trustFailed
    case removalFailed

    var errorDescription: String? {
        switch self {
        case .generationFailed(let reason):
            return "Failed to generate CA certificate: \(reason)"
        case .pkcs12Failed:
            return "Failed to create PKCS12 file"
        case .keychainAddFailed(let reason):
            return "Failed to add certificate to Keychain: \(reason)"
        case .trustFailed:
            return "Failed to set trust settings"
        case .removalFailed:
            return "Failed to remove certificate from Keychain"
        }
    }
}
