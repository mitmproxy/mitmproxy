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
        // Check if MDM says CA is already installed via configuration profile
        if MDMConfigService.shared.managedCACertInstalled {
            print("[CertificateService] CA marked as installed via MDM profile")
            isCAGenerated = true
            isCAInstalled = true
            return
        }

        let fm = FileManager.default
        let keyExists = fm.fileExists(atPath: Constants.caKeyPath.path)
        let certExists = fm.fileExists(atPath: Constants.caCertPath.path)

        if keyExists && certExists {
            // Validate and attempt repair if needed
            isCAGenerated = validateAndRepairCA()
        } else {
            isCAGenerated = false
        }

        isCAInstalled = isCAInKeychain()
    }

    /// Validate and repair the CA certificate if needed
    /// mitmproxy expects oximy-ca.pem to contain BOTH key and cert concatenated
    /// Returns true if certificate is valid or was successfully repaired
    private func validateAndRepairCA() -> Bool {
        let keyPath = Constants.caKeyPath  // oximy-ca.pem (should have key+cert)
        let certPath = Constants.caCertPath // oximy-ca-cert.pem (cert only)

        // Check if combined file exists and has correct format
        guard let content = try? String(contentsOf: keyPath, encoding: .utf8) else {
            return false
        }

        let hasKey = content.contains("-----BEGIN PRIVATE KEY-----") ||
                     content.contains("-----BEGIN RSA PRIVATE KEY-----")
        let hasCert = content.contains("-----BEGIN CERTIFICATE-----")

        if hasKey && hasCert {
            return true  // Already valid
        }

        // Try to repair: if we have key in one file and cert in another
        if hasKey && !hasCert {
            if let certContent = try? String(contentsOf: certPath, encoding: .utf8),
               certContent.contains("-----BEGIN CERTIFICATE-----") {
                // Repair by concatenating
                let combined = content + certContent
                do {
                    try combined.write(to: keyPath, atomically: true, encoding: .utf8)
                    NSLog("[CertificateService] Repaired oximy-ca.pem by adding certificate")
                    OximyLogger.shared.log(.CERT_STATE_105, "CA certificate repaired")
                    return true
                } catch {
                    NSLog("[CertificateService] Failed to repair certificate: \(error)")
                }
            }
        }

        NSLog("[CertificateService] Certificate file is invalid - needs regeneration")
        return false
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
    /// mitmproxy expects oximy-ca.pem to contain BOTH key and cert concatenated
    func generateCA() async throws {
        // Ensure directory exists
        let fm = FileManager.default
        if !fm.fileExists(atPath: Constants.oximyDir.path) {
            try fm.createDirectory(at: Constants.oximyDir, withIntermediateDirectories: true)
        }

        // Skip if already exists and is valid
        if fm.fileExists(atPath: Constants.caCertPath.path) &&
           fm.fileExists(atPath: Constants.caKeyPath.path) {
            // Verify the combined file has both key and cert
            if let content = try? String(contentsOf: Constants.caKeyPath, encoding: .utf8),
               (content.contains("-----BEGIN PRIVATE KEY-----") ||
                content.contains("-----BEGIN RSA PRIVATE KEY-----")) &&
               content.contains("-----BEGIN CERTIFICATE-----") {
                isCAGenerated = true
                return
            }
            // If not valid, regenerate
            NSLog("[CertificateService] Regenerating CA - combined file invalid or incomplete")
        }

        // Temporary paths for separate key and cert generation
        let tempKeyPath = Constants.oximyDir.appendingPathComponent("temp-key.pem")
        let tempCertPath = Constants.oximyDir.appendingPathComponent("temp-cert.pem")

        // Generate CA using OpenSSL (key and cert to temp files)
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/openssl")
        process.arguments = [
            "req", "-x509", "-new", "-nodes",
            "-newkey", "rsa:4096",
            "-keyout", tempKeyPath.path,
            "-out", tempCertPath.path,
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

            // Read the generated files
            let keyData = try String(contentsOf: tempKeyPath, encoding: .utf8)
            let certData = try String(contentsOf: tempCertPath, encoding: .utf8)

            // mitmproxy expects oximy-ca.pem to have: key + cert concatenated
            // Format: private key first, then certificate
            let combinedPEM = keyData + certData
            try combinedPEM.write(to: Constants.caKeyPath, atomically: true, encoding: .utf8)

            // Also keep the cert-only file for Keychain installation and other uses
            try certData.write(to: Constants.caCertPath, atomically: true, encoding: .utf8)

            // Set appropriate permissions (key file should be readable only by owner)
            try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: Constants.caKeyPath.path)
            try fm.setAttributes([.posixPermissions: 0o644], ofItemAtPath: Constants.caCertPath.path)

            // Create a PKCS12 version for easier import (using temp files before cleanup)
            try await createPKCS12(keyPath: tempKeyPath, certPath: tempCertPath)

            // Clean up temp files
            try? fm.removeItem(at: tempKeyPath)
            try? fm.removeItem(at: tempCertPath)

            isCAGenerated = true
            lastError = nil
            print("[CertificateService] CA generated successfully (combined PEM format)")

            OximyLogger.shared.log(.CERT_STATE_101, "CA certificate generated")
            OximyLogger.shared.setTag("cert_generated", value: "true")

        } catch {
            // Clean up temp files on error
            try? fm.removeItem(at: tempKeyPath)
            try? fm.removeItem(at: tempCertPath)

            lastError = error.localizedDescription
            SentryService.shared.captureError(error, context: [
                "operation": "ca_generate",
                "ca_path": Constants.caCertPath.path
            ])
            throw error
        }
    }

    /// Create PKCS12 file for Keychain import
    private func createPKCS12(keyPath: URL, certPath: URL) async throws {
        let p12Path = Constants.oximyDir.appendingPathComponent("oximy-ca.p12")

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/openssl")
        process.arguments = [
            "pkcs12", "-export",
            "-inkey", keyPath.path,
            "-in", certPath.path,
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
    /// This will prompt the user for their password (unless MDM has pre-installed)
    func installCA() async throws {
        // Check if MDM says CA is already installed via configuration profile
        if MDMConfigService.shared.managedCACertInstalled {
            print("[CertificateService] CA already installed via MDM - skipping installation")
            isCAInstalled = true
            lastError = nil
            return
        }

        if !isCAGenerated {
            try await generateCA()
        }

        do {
            // Method 1: Use security command to add and trust the certificate
            // This triggers the standard macOS password prompt
            try await addCertToKeychain()
            try await trustCertInKeychain()

            isCAInstalled = true
            lastError = nil
            print("[CertificateService] CA installed to Keychain")

            OximyLogger.shared.log(.CERT_STATE_102, "CA installed to Keychain", data: [
                "keychain_type": "system"
            ])
            OximyLogger.shared.setTag("cert_installed", value: "true")
        } catch {
            SentryService.shared.captureError(error, context: [
                "operation": "ca_install"
            ])
            throw error
        }
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
                OximyLogger.shared.log(.CERT_WARN_201, "System keychain failed, falling back to user keychain")
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
            let error = CertificateError.removalFailed
            SentryService.shared.captureError(error, context: [
                "operation": "ca_remove",
                "sec_status": status
            ])
            throw error
        }

        isCAInstalled = false
        print("[CertificateService] CA removed from Keychain")

        SentryService.shared.addStateBreadcrumb(
            category: "certificate",
            message: "CA removed from Keychain"
        )
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

        let p12Path = Constants.oximyDir.appendingPathComponent("oximy-ca.p12")
        if fm.fileExists(atPath: p12Path.path) {
            try fm.removeItem(at: p12Path)
        }

        // Also remove DH params file that mitmproxy creates
        let dhParamPath = Constants.oximyDir.appendingPathComponent("oximy-dhparam.pem")
        if fm.fileExists(atPath: dhParamPath.path) {
            try fm.removeItem(at: dhParamPath)
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
